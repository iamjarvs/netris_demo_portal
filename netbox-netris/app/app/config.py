"""Loads config/config.yaml (tunables) + environment variables (secrets) into one
dot-accessible settings object. YAML holds everything the user might reasonably want
to change; env vars hold only credentials/URLs.
"""
import os
import types

import yaml

DEFAULT_CONFIG_PATH = os.environ.get("SYNC_CONFIG_PATH", "/app/config/config.yaml")


def _to_namespace(d):
    if isinstance(d, dict):
        ns = types.SimpleNamespace()
        for k, v in d.items():
            setattr(ns, k, _to_namespace(v))
        return ns
    return d


def _ns_to_dict(ns):
    if isinstance(ns, dict):
        return ns
    return vars(ns) if ns else {}


def _default(ns, key, value):
    if not hasattr(ns, key) or getattr(ns, key) is None:
        setattr(ns, key, value)


def load_config(path=None):
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    cfg = _to_namespace(raw)

    if not hasattr(cfg, "sync"):
        cfg.sync = types.SimpleNamespace()
    _default(cfg.sync, "netbox_poll_interval_seconds", 60)
    _default(cfg.sync, "netris_poll_interval_seconds", 60)
    _default(cfg.sync, "full_reconcile_interval_seconds", 1800)
    _default(cfg.sync, "push_custom_field", "push_to_netris")
    _default(cfg.sync, "vpc_custom_field", "netris_vpc")
    _default(cfg.sync, "netbox_origin_tag_on_netris", "source-netbox")
    _default(cfg.sync, "netris_origin_tag_on_netbox", "source-netris")
    _default(cfg.sync, "enrich_netbox_custom_fields", True)
    _default(cfg.sync, "seed_netbox_on_startup", False)
    _default(cfg.sync, "import_existing_netris_ipam", True)
    _default(cfg.sync, "on_netbox_prefix_removed", "flag_for_review")
    _default(cfg.sync, "on_netris_reservation_removed", "deprecate")
    _default(cfg.sync, "on_netris_subnet_removed", "deprecate")

    if not hasattr(cfg, "mapping"):
        cfg.mapping = types.SimpleNamespace()
    cfg.mapping.sites = _ns_to_dict(getattr(cfg.mapping, "sites", {}))
    cfg.mapping.tenants = _ns_to_dict(getattr(cfg.mapping, "tenants", {}))
    _default(cfg.mapping, "default_tenant_id", None)

    cfg.role_to_purpose = _ns_to_dict(getattr(cfg, "role_to_purpose", {}))

    if not hasattr(cfg, "logging"):
        cfg.logging = types.SimpleNamespace()
    _default(cfg.logging, "level", "INFO")

    cfg.secrets = types.SimpleNamespace(
        netbox_url=os.environ["NETBOX_URL"],
        netbox_superuser_name=os.environ.get("NETBOX_SUPERUSER_NAME", "admin"),
        netbox_superuser_password=os.environ["NETBOX_SUPERUSER_PASSWORD"],
        netris_url=os.environ["NETRIS_URL"],
        netris_user=os.environ["NETRIS_USER"],
        netris_password=os.environ["NETRIS_PASSWORD"],
    )
    cfg.paths = types.SimpleNamespace(
        sqlite_path=os.environ.get("SYNC_DB_PATH", "/app/data/mapping.db"),
        netbox_token_cache_path=os.environ.get("NETBOX_TOKEN_CACHE_PATH", "/app/data/netbox_token"),
    )
    return cfg
