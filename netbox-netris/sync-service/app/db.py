import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, SyncedObject, SyncRun


class MappingStore:
    """Thin repository over the local mapping DB (SQLite). Each call opens and closes
    its own session - this service's sync jobs are sequential (max_instances=1 in the
    scheduler), so there's no meaningful concurrency to worry about here.
    """

    def __init__(self, sqlite_path):
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
        Base.metadata.create_all(self.engine)
        self._migrate()
        self.Session = sessionmaker(bind=self.engine, future=True)

    def _migrate(self):
        """create_all() only creates missing tables, not missing columns on an
        already-existing one - add any columns introduced after a database already
        exists on disk here."""
        with self.engine.connect() as conn:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(synced_objects)").fetchall()}
            if "vpc_id" not in cols:
                conn.exec_driver_sql("ALTER TABLE synced_objects ADD COLUMN vpc_id INTEGER")
                conn.commit()

    @contextmanager
    def session(self):
        s = self.Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def get_mapping(self, direction, netbox_type=None, netbox_id=None, netris_type=None, netris_id=None):
        with self.session() as s:
            q = s.query(SyncedObject).filter(SyncedObject.direction == direction)
            if netbox_id is not None:
                q = q.filter(SyncedObject.netbox_type == netbox_type, SyncedObject.netbox_id == netbox_id)
            if netris_id is not None:
                q = q.filter(SyncedObject.netris_type == netris_type, SyncedObject.netris_id == netris_id)
            row = q.first()
            if row:
                s.expunge(row)
            return row

    def upsert_mapping(self, direction, netbox_type, netbox_id, netris_type, netris_id, content_hash, status="synced", vpc_id=None):
        with self.session() as s:
            q = s.query(SyncedObject).filter(SyncedObject.direction == direction)
            if netbox_id is not None:
                q = q.filter(SyncedObject.netbox_type == netbox_type, SyncedObject.netbox_id == netbox_id)
            else:
                q = q.filter(SyncedObject.netris_type == netris_type, SyncedObject.netris_id == netris_id)
            row = q.first()
            if row:
                row.netris_id = netris_id
                row.netbox_id = netbox_id if netbox_id is not None else row.netbox_id
                row.content_hash = content_hash
                row.status = status
                row.vpc_id = vpc_id
            else:
                row = SyncedObject(
                    direction=direction,
                    netbox_type=netbox_type,
                    netbox_id=netbox_id,
                    netris_type=netris_type,
                    netris_id=netris_id,
                    content_hash=content_hash,
                    status=status,
                    vpc_id=vpc_id,
                )
                s.add(row)

    def get_stale_netris_mappings(self, direction, netris_type, seen_ids):
        with self.session() as s:
            q = s.query(SyncedObject).filter(
                SyncedObject.direction == direction,
                SyncedObject.netris_type == netris_type,
                SyncedObject.status == "synced",
            )
            rows = [r for r in q.all() if r.netris_id not in seen_ids]
            for r in rows:
                s.expunge(r)
            return rows

    def get_stale_push_mappings(self, netbox_type, seen_netbox_ids):
        with self.session() as s:
            q = s.query(SyncedObject).filter(
                SyncedObject.direction == "netbox_to_netris",
                SyncedObject.netbox_type == netbox_type,
                SyncedObject.status == "synced",
            )
            rows = [r for r in q.all() if r.netbox_id not in seen_netbox_ids]
            for r in rows:
                s.expunge(r)
            return rows

    def mark_stale(self, row_id):
        with self.session() as s:
            row = s.get(SyncedObject, row_id)
            if row:
                row.status = "deprecated"

    def flag_for_review(self, row_id):
        with self.session() as s:
            row = s.get(SyncedObject, row_id)
            if row:
                row.status = "flagged_for_review"

    def start_run(self, direction):
        with self.session() as s:
            run = SyncRun(direction=direction, status="running")
            s.add(run)
            s.flush()
            return run.id

    def finish_run(self, run_id, status, summary=None, error=None):
        with self.session() as s:
            run = s.get(SyncRun, run_id)
            if run:
                run.status = status
                run.summary = summary
                run.error = error
                run.finished_at = datetime.now(timezone.utc)

    def recent_runs(self, limit=20):
        with self.session() as s:
            rows = s.query(SyncRun).order_by(SyncRun.id.desc()).limit(limit).all()
            for r in rows:
                s.expunge(r)
            return rows
