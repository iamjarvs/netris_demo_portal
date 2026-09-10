import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .sync_pull import pull_netris_to_netbox
from .sync_push import push_netbox_to_netris

logger = logging.getLogger(__name__)


def _run_job(name, fn, nb, netris, db, cfg):
    run_id = db.start_run(name)
    try:
        fn(nb, netris, db, cfg)
        db.finish_run(run_id, "ok")
    except Exception as exc:
        logger.exception("Sync job %s failed", name)
        db.finish_run(run_id, "error", error=str(exc))


def start_scheduler(nb, netris, db, cfg):
    scheduler = BackgroundScheduler()
    now = datetime.now(timezone.utc)

    scheduler.add_job(
        _run_job,
        "interval",
        seconds=cfg.sync.netbox_poll_interval_seconds,
        args=["netbox_to_netris", push_netbox_to_netris, nb, netris, db, cfg],
        id="push_netbox_to_netris",
        max_instances=1,
        coalesce=True,
        next_run_time=now,
    )
    scheduler.add_job(
        _run_job,
        "interval",
        seconds=cfg.sync.netris_poll_interval_seconds,
        args=["netris_to_netbox", pull_netris_to_netbox, nb, netris, db, cfg],
        id="pull_netris_to_netbox",
        max_instances=1,
        coalesce=True,
        next_run_time=now,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: netbox->netris every %ss, netris->netbox every %ss",
        cfg.sync.netbox_poll_interval_seconds,
        cfg.sync.netris_poll_interval_seconds,
    )
    return scheduler
