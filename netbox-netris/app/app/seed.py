"""Idempotently creates a small, representative AI-cluster IPAM plan in NetBox so
there's something real to look at (and to push to Netris) on first boot. Every
get-or-create here is safe to re-run - nothing is duplicated on restart.
"""
import logging

logger = logging.getLogger(__name__)

# NetBox slugs here intentionally match config.yaml's default `mapping:` block
# (datacenter-a / ai-cluster-demo) so the out-of-the-box config is self-consistent.
SITE_SLUG = "datacenter-a"
SITE_NAME = "Datacenter-A"
TENANT_SLUG = "ai-cluster-demo"
TENANT_NAME = "AI Cluster Demo"

SEED_PREFIXES = [
    ("10.0.0.0/16", "loopback", "Underlay loopbacks"),
    ("10.1.0.0/16", "management", "Out-of-band management"),
    ("10.2.0.0/16", "gpu-frontend", "GPU cluster frontend / storage fabric"),
    ("10.3.0.0/16", "gpu-backend", "GPU cluster backend / RDMA fabric"),
    ("10.4.0.0/16", "bgp-underlay", "eBGP underlay point-to-points"),
]

ROLES = [
    ("loopback", "Loopback"),
    ("management", "Management"),
    ("bgp-underlay", "BGP Underlay"),
    ("gpu-frontend", "GPU Cluster Frontend"),
    ("gpu-backend", "GPU Cluster Backend"),
]


def seed_netbox(nb_api, cfg):
    tenant = nb_api.tenancy.tenants.get(slug=TENANT_SLUG) or nb_api.tenancy.tenants.create(
        name=TENANT_NAME, slug=TENANT_SLUG
    )

    site = nb_api.dcim.sites.get(slug=SITE_SLUG) or nb_api.dcim.sites.create(
        name=SITE_NAME, slug=SITE_SLUG, status="active"
    )

    rir = nb_api.ipam.rirs.get(slug="rfc1918") or nb_api.ipam.rirs.create(
        name="RFC1918", slug="rfc1918", is_private=True
    )

    roles = {}
    for role_slug, role_name in ROLES:
        roles[role_slug] = nb_api.ipam.roles.get(slug=role_slug) or nb_api.ipam.roles.create(
            name=role_name, slug=role_slug
        )

    push_field = cfg.sync.push_custom_field

    if not nb_api.ipam.aggregates.get(prefix="10.0.0.0/8"):
        nb_api.ipam.aggregates.create(
            prefix="10.0.0.0/8",
            rir=rir.id,
            tenant=tenant.id,
            description="AI fabric address space",
            custom_fields={push_field: True},
        )

    for prefix, role_slug, desc in SEED_PREFIXES:
        if nb_api.ipam.prefixes.get(prefix=prefix):
            continue
        nb_api.ipam.prefixes.create(
            prefix=prefix,
            # NetBox 4.2+ replaced the direct `site` FK on Prefix with a generic
            # scope (scope_type/scope_id) that can point at a Site, Region, etc.
            scope_type="dcim.site",
            scope_id=site.id,
            tenant=tenant.id,
            role=roles[role_slug].id,
            status="active",
            description=desc,
            custom_fields={push_field: True},
        )

    logger.info("NetBox seed data ensured (tenant=%s, site=%s)", tenant.slug, site.slug)
