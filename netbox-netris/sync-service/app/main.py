import logging
import sys

import uvicorn
from fastapi import FastAPI

from . import bootstrap
from .config import load_config
from .db import MappingStore
from .netbox_client import NetBoxClient
from .netris_client import NetrisClient
from .scheduler import start_scheduler
from .seed import seed_netbox
from .sync_push import push_netbox_to_netris
from .vpc_choices import sync_vpc_choices

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sync-service")

cfg = load_config()
logging.getLogger().setLevel(cfg.logging.level)

app = FastAPI(title="NetBox <-> Netris Sync")

db = MappingStore(cfg.paths.sqlite_path)
netris = NetrisClient(cfg.secrets.netris_url, cfg.secrets.netris_user, cfg.secrets.netris_password)

# Set once NetBox is reachable and a working API token has been obtained - see
# bootstrap.py for why this isn't just a static token from an env var.
nb = None
_scheduler = None


@app.on_event("startup")
def on_startup():
    global nb, _scheduler

    try:
        bootstrap.wait_for_netbox(cfg.secrets.netbox_url)
    except RuntimeError:
        logger.error("NetBox never became reachable, exiting")
        sys.exit(1)

    token = bootstrap.get_or_provision_token(
        cfg.secrets.netbox_url,
        cfg.secrets.netbox_superuser_name,
        cfg.secrets.netbox_superuser_password,
        cfg.paths.netbox_token_cache_path,
    )
    nb = NetBoxClient(cfg.secrets.netbox_url, token)

    # NetBox does NOT auto-create tags referenced by name in a nested write (that was
    # an incorrect assumption) - every tag this service ever writes has to exist
    # ahead of time, regardless of whether seeding is on.
    for tag_name in (
        cfg.sync.netbox_origin_tag_on_netris,
        cfg.sync.netris_origin_tag_on_netbox,
    ):
        nb.get_or_create_tag(tag_name)

    # The opt-in "push this to Netris" signal is a checkbox, not a tag - far more
    # discoverable on a prefix/aggregate's edit form than a magic tag name.
    nb.ensure_custom_field(
        name=cfg.sync.push_custom_field,
        label="Push to Netris?",
        object_types=["ipam.prefix", "ipam.aggregate"],
        cf_type="boolean",
        default=False,
        description="Check to push this prefix/aggregate to Netris on the next sync cycle.",
    )

    # Which Netris VPC to push into - a dropdown populated from Netris's real VPC list
    # (never hard-coded to one), refreshed every poll cycle by vpc_choices.py. Needs the
    # choice set to exist (with real choices) before the field is created, so it isn't
    # left pointing at an empty dropdown on first boot.
    try:
        vpc_choice_set = sync_vpc_choices(nb, netris, cfg)
        nb.ensure_custom_field(
            name=cfg.sync.vpc_custom_field,
            label="Netris VPC",
            object_types=["ipam.prefix", "ipam.aggregate"],
            cf_type="select",
            choice_set_id=vpc_choice_set.id,
            description="Which Netris VPC to push this into. Leave blank for Netris's Default VPC.",
        )
    except Exception:
        logger.exception("Could not set up the Netris VPC picker (continuing without it)")

    if cfg.sync.seed_netbox_on_startup:
        try:
            seed_netbox(nb.api, cfg)
        except Exception:
            logger.exception("NetBox seeding failed (continuing without it)")

    if cfg.sync.enrich_netbox_custom_fields:
        nb.ensure_custom_field(
            name="netris_id",
            label="Netris Object ID",
            object_types=["ipam.prefix", "ipam.aggregate", "ipam.ipaddress"],
        )

    _scheduler = start_scheduler(nb, netris, db, cfg)


@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    runs = db.recent_runs(limit=20)
    return {
        "config": {
            "netbox_poll_interval_seconds": cfg.sync.netbox_poll_interval_seconds,
            "netris_poll_interval_seconds": cfg.sync.netris_poll_interval_seconds,
            "push_custom_field": cfg.sync.push_custom_field,
        },
        "recent_runs": [
            {
                "id": r.id,
                "direction": r.direction,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error": r.error,
            }
            for r in runs
        ],
    }


@app.post("/webhooks/netbox")
def netbox_webhook(payload: dict):
    """Optional fast-path: point a NetBox Event Rule at this endpoint (Admin ->
    Operations -> Event Rules) to trigger an immediate push instead of waiting for the
    next poll. Not required for correctness - the scheduled poller covers this
    independently every netbox_poll_interval_seconds regardless.
    """
    logger.info("Received NetBox webhook for %s %s", payload.get("model"), payload.get("event"))
    if nb is None:
        logger.warning("Ignoring webhook - startup hasn't finished yet")
        return {"accepted": False}
    try:
        push_netbox_to_netris(nb, netris, db, cfg)
    except Exception:
        logger.exception("Webhook-triggered push failed")
    return {"accepted": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
