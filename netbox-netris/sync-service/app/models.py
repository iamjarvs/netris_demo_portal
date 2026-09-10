from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class SyncedObject(Base):
    """Correlates one NetBox object with one Netris object, in one sync direction.

    This table is the authoritative source of truth for "have we already synced this,
    and did anything change since." The optional NetBox custom-field enrichment
    (config: enrich_netbox_custom_fields) is purely a UI convenience layered on top.
    """

    __tablename__ = "synced_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    direction = Column(String, nullable=False)  # netbox_to_netris | netris_to_netbox
    netbox_type = Column(String, nullable=True)  # prefix | aggregate | ipaddress
    netbox_id = Column(Integer, nullable=True)
    netris_type = Column(String, nullable=True)  # subnet | allocation | reservation
    netris_id = Column(Integer, nullable=True)
    # The Netris VPC id this object was last successfully pushed into. Netris silently
    # ignores a "vpc" change on PUT (verified empirically - returns 200 but doesn't move
    # the object), so this is compared against the newly-resolved vpc on each push to
    # detect a real change and trigger delete+recreate instead of a no-op update.
    vpc_id = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True)
    status = Column(String, default="synced")  # synced | flagged_for_review | deprecated
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    direction = Column(String, nullable=False)
    started_at = Column(DateTime, default=_now)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # running | ok | error
    summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
