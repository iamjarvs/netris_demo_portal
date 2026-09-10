"""Getting a working NetBox API token without depending on netbox-docker's
SUPERUSER_API_TOKEN env var, which has an open bug on NetBox 4.5+ where the fixed
token value it's given is sometimes ignored (netbox-community/netbox-docker#1589) -
NetBox silently generates a random, unknown-to-us token instead.

Instead: NetBox is only told to create the superuser account (username + password,
which works reliably), and this service exchanges those credentials for a real token
at runtime via pynetbox's own `Api.create_token()`, which wraps NetBox's documented
POST /api/users/tokens/provision/ endpoint. This matters more than it sounds: NetBox
4.5+ introduced a "v2" token scheme where the provisioning response contains a `key`
(a 12-char public identifier) and a separate `token` (the 40-char secret) - the actual
Authorization header value is `Bearer nbt_<key>.<token>`, not the classic
`Token <key>`. Hand-rolling this was tried first and got a confusing, silent-looking
"Invalid v1 token" 403 from NetBox (it was authenticating with the 12-char identifier
alone). pynetbox 7.8.0 already builds this value correctly via create_token(), so this
just uses that instead of reimplementing it.

The obtained token is cached to disk so restarts don't mint a fresh one every time.
"""
import logging
import os
import time

import pynetbox
import requests

logger = logging.getLogger(__name__)


def wait_for_netbox(base_url, max_attempts=60, delay_seconds=5):
    url = f"{base_url.rstrip('/')}/login/"
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                logger.info("NetBox is reachable")
                return
        except requests.RequestException:
            pass
        logger.info("Waiting for NetBox... (%s/%s)", attempt + 1, max_attempts)
        time.sleep(delay_seconds)
    raise RuntimeError("NetBox never became reachable")


def get_or_provision_token(base_url, username, password, cache_path):
    base_url = base_url.rstrip("/")

    cached = _read_cached_token(cache_path)
    if cached and _token_is_valid(base_url, cached):
        logger.info("Using cached NetBox API token")
        return cached

    logger.info("Provisioning a fresh NetBox API token for %s", username)
    api = pynetbox.api(base_url)
    api.create_token(username, password)  # sets api.token to the full auth value -
    # `nbt_<key>.<token>` on NetBox 4.5+, or the plain token on older versions
    _write_cached_token(cache_path, api.token)
    return api.token


def _read_cached_token(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            value = f.read().strip()
            return value or None
    return None


def _write_cached_token(cache_path, token):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        f.write(token)
    os.chmod(cache_path, 0o600)


def _token_is_valid(base_url, token):
    try:
        pynetbox.api(base_url, token=token).status()
        return True
    except Exception:
        return False
