"""Netris -> NetBox: pull the IP Reservation ledger (the canonical "what's assigned to
what" record in Netris - covers vnet/bgp/hw/nat/roh/l4lb consumers) and mirror each
reservation into a NetBox IP Address, tagged as Netris-originated.

Netris is the source of truth for actual host/interface assignment once deployed, so
this direction creates/updates freely. A reservation that disappears (host decommissioned)
marks the NetBox IP Address deprecated rather than deleting it - see config:
on_netris_reservation_removed.
"""
import logging

from .sync_import import import_netris_to_netbox
from .vpc_choices import sync_vpc_choices

logger = logging.getLogger(__name__)

_hw_name_cache = {}


def _resolve_hw_name(netris, hw_id):
    if hw_id in _hw_name_cache:
        return _hw_name_cache[hw_id]
    try:
        hw = netris.get_hw(hw_id)
        name = hw.get("name") if hw else None
    except Exception:
        name = None
    _hw_name_cache[hw_id] = name
    return name


def _describe_consumer(netris, consumer):
    ctype = consumer.get("type", "unknown")
    cid = consumer.get("id")
    if ctype == "hw" and cid:
        name = _resolve_hw_name(netris, cid)
        return f"Netris: {name or ('hw#' + str(cid))}"
    return f"Netris: {ctype}" + (f"#{cid}" if cid else "")


def pull_netris_to_netbox(nb, netris, db, cfg):
    try:
        sync_vpc_choices(nb, netris, cfg)
    except Exception:
        logger.exception("Failed to refresh the Netris VPC picker (continuing)")

    if cfg.sync.import_existing_netris_ipam:
        try:
            import_netris_to_netbox(nb, netris, db, cfg)
        except Exception:
            logger.exception("Failed to import Netris's existing IPAM plan (continuing with reservations)")

    reservations = netris.list_reservations()
    seen_ids = set()

    for res in reservations:
        try:
            if _sync_one_reservation(nb, netris, db, cfg, res):
                seen_ids.add(res.get("id"))
        except Exception:
            logger.exception("Failed to sync Netris reservation %s", res.get("id"))

    _handle_removed(nb, db, cfg, seen_ids)


def _sync_one_reservation(nb, netris, db, cfg, res):
    res_id = res.get("id")
    host = res.get("host") or {}
    address = host.get("address")
    subnet = host.get("subnet") or {}
    prefix_str = subnet.get("prefix")  # e.g. "10.2.3.0/24"
    if not address or not prefix_str or "/" not in prefix_str:
        return False

    length = prefix_str.split("/", 1)[1]
    cidr = f"{address}/{length}"
    description = _describe_consumer(netris, res.get("consumer") or {})
    content_hash = f"{cidr}|{description}"

    row = db.get_mapping(direction="netris_to_netbox", netris_type="reservation", netris_id=res_id)
    if row and row.content_hash == content_hash:
        return True

    if row and row.netbox_id:
        ip_obj = nb.api.ipam.ip_addresses.get(id=row.netbox_id)
        if ip_obj:
            nb.update_ip_address(ip_obj, status="active", description=description)
            action = "updated"
        else:
            ip_obj = _create_ip(nb, cfg, cidr, description)
            action = "recreated"
    else:
        existing = nb.find_ip_address(cidr)
        ip_obj = existing or _create_ip(nb, cfg, cidr, description)
        action = "linked existing" if existing else "created"

    if not ip_obj:
        return False

    db.upsert_mapping("netris_to_netbox", "ipaddress", ip_obj.id, "reservation", res_id, content_hash)
    logger.info("%s NetBox IP %s from Netris reservation %s", action, cidr, res_id)
    return True


def _create_ip(nb, cfg, cidr, description):
    return nb.create_ip_address(
        address=cidr,
        status="active",
        tags=[{"name": cfg.sync.netris_origin_tag_on_netbox}],
        description=description,
    )


def _handle_removed(nb, db, cfg, seen_ids):
    for row in db.get_stale_netris_mappings("netris_to_netbox", "reservation", seen_ids):
        if cfg.sync.on_netris_reservation_removed == "deprecate":
            ip_obj = nb.api.ipam.ip_addresses.get(id=row.netbox_id)
            if ip_obj and getattr(ip_obj.status, "value", ip_obj.status) != "deprecated":
                nb.update_ip_address(ip_obj, status="deprecated")
                logger.info(
                    "Deprecated NetBox IP %s (Netris reservation %s no longer present)",
                    ip_obj.address, row.netris_id,
                )
        db.mark_stale(row.id)
