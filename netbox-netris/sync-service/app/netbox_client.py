"""Thin wrapper around pynetbox, exposing only what the sync jobs need."""
import logging
import re

import pynetbox

logger = logging.getLogger(__name__)


def slugify(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unnamed"


class NetBoxClient:
    def __init__(self, url, token):
        self.api = pynetbox.api(url, token=token)

    def prefixes_flagged_for_push(self, field_name):
        return list(self.api.ipam.prefixes.filter(**{f"cf_{field_name}": True}))

    def aggregates_flagged_for_push(self, field_name):
        return list(self.api.ipam.aggregates.filter(**{f"cf_{field_name}": True}))

    def get_or_create_tag(self, name, color="9e9e9e"):
        slug = slugify(name)
        return self.api.extras.tags.get(slug=slug) or self.api.extras.tags.create(
            name=name, slug=slug, color=color
        )

    def get_or_create_tenant(self, name):
        slug = slugify(name)
        return self.api.tenancy.tenants.get(slug=slug) or self.api.tenancy.tenants.create(
            name=name, slug=slug
        )

    def get_or_create_site(self, name):
        slug = slugify(name)
        return self.api.dcim.sites.get(slug=slug) or self.api.dcim.sites.create(
            name=name, slug=slug, status="active"
        )

    def get_or_create_role(self, name):
        slug = slugify(name)
        return self.api.ipam.roles.get(slug=slug) or self.api.ipam.roles.create(name=name, slug=slug)

    def get_or_create_rir(self, name, is_private=True):
        slug = slugify(name)
        return self.api.ipam.rirs.get(slug=slug) or self.api.ipam.rirs.create(
            name=name, slug=slug, is_private=is_private
        )

    def find_aggregate(self, prefix):
        return self.api.ipam.aggregates.get(prefix=prefix)

    def create_aggregate(self, **fields):
        return self.api.ipam.aggregates.create(**fields)

    def find_prefix(self, prefix):
        return self.api.ipam.prefixes.get(prefix=prefix)

    def create_prefix(self, **fields):
        return self.api.ipam.prefixes.create(**fields)

    def ensure_custom_field(self, name, label, object_types, cf_type="text", default=None, description="", choice_set_id=None):
        try:
            existing = self.api.extras.custom_fields.get(name=name)
            if existing:
                return existing
            payload = dict(name=name, label=label, type=cf_type, object_types=object_types, description=description)
            if default is not None:
                payload["default"] = default
            if choice_set_id is not None:
                payload["choice_set"] = choice_set_id
            return self.api.extras.custom_fields.create(**payload)
        except Exception as exc:
            logger.warning("Could not ensure custom field %s (non-fatal): %s", name, exc)
            return None

    def get_or_create_choice_set(self, name, extra_choices):
        """extra_choices: list of [value, label] pairs. Returns the choice set, creating
        it if missing - callers should follow up with update_choice_set() to refresh the
        options on every run (this only handles first-time creation)."""
        existing = self.api.extras.custom_field_choice_sets.get(name=name)
        if existing:
            return existing
        return self.api.extras.custom_field_choice_sets.create(name=name, extra_choices=extra_choices)

    def update_choice_set(self, choice_set, extra_choices):
        if list(choice_set.extra_choices) == list(extra_choices):
            return False
        choice_set.extra_choices = extra_choices
        choice_set.save()
        return True

    def get_site(self, site_id):
        return self.api.dcim.sites.get(id=site_id)

    def find_ip_address(self, address):
        return self.api.ipam.ip_addresses.get(address=address)

    def create_ip_address(self, address, status, tags, description):
        return self.api.ipam.ip_addresses.create(
            address=address, status=status, tags=tags, description=description
        )

    def update_ip_address(self, ip_obj, **fields):
        for k, v in fields.items():
            setattr(ip_obj, k, v)
        ip_obj.save()
        return ip_obj
