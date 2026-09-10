"""Netris -> NetBox: mirror Netris's EXISTING IPAM plan (allocations + subnets) into
NetBox, so the demo environment reflects your real address space instead of starting
from nothing. Runs as part of every Netris->NetBox poll cycle (see sync_pull.py), so
it's current every time this service starts or ticks - not just seeded once.

Mirrored objects are tagged `netris_origin_tag_on_netbox` and deliberately left
UNCHECKED for `push_custom_field` ("Push to Netris?") - that's what stops
sync_push.py from ever trying to push a mirrored object back out to Netris as if
NetBox had authored it. Add a genuinely new prefix in NetBox and check that box on
*that* one and it'll flow out to Netris; the mirrored ones never do.
"""
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def _hash(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _flatten_subnets(node, acc):
    for child in node.get("children") or []:
        if child.get("type") == "subnet":
            acc.append(child)
        _flatten_subnets(child, acc)


def import_netris_to_netbox(nb, netris, db, cfg):
    # GET /api/v2/ipam silently only returns the Default VPC's data unless every VPC id
    # is passed explicitly (verified empirically - a real non-default-VPC allocation was
    # completely invisible otherwise). Fetch the current VPC list every run rather than
    # caching it, so a newly created VPC is picked up without a restart.
    vpc_ids = [v["id"] for v in netris.list_vpcs() if v.get("id")]
    tree = netris.get_ipam_tree(vpc_ids=vpc_ids)
    rir = nb.get_or_create_rir("Netris")

    seen_allocation_ids = set()
    seen_subnet_ids = set()

    for allocation in tree:
        try:
            if _import_allocation(nb, db, cfg, rir, allocation):
                seen_allocation_ids.add(allocation.get("id"))
        except Exception:
            logger.exception(
                "Failed to import Netris allocation %s (%s)", allocation.get("id"), allocation.get("prefix")
            )

        subnets = []
        _flatten_subnets(allocation, subnets)
        for subnet in subnets:
            try:
                if _import_subnet(nb, db, cfg, subnet):
                    seen_subnet_ids.add(subnet.get("id"))
            except Exception:
                logger.exception(
                    "Failed to import Netris subnet %s (%s)", subnet.get("id"), subnet.get("prefix")
                )

    _handle_removed(nb, db, cfg, "allocation", seen_allocation_ids)
    _handle_removed(nb, db, cfg, "subnet", seen_subnet_ids)


def _import_allocation(nb, db, cfg, rir, allocation):
    netris_id = allocation.get("id")
    prefix = allocation.get("prefix")
    if not prefix:
        return False

    tenant_name = (allocation.get("tenant") or {}).get("name") or "Netris"
    tenant = nb.get_or_create_tenant(tenant_name)

    body = {
        "prefix": prefix,
        "rir": rir.id,
        "tenant": tenant.id,
        "description": allocation.get("name") or prefix,
    }
    content_hash = _hash(body)

    row = db.get_mapping(direction="netris_import", netris_type="allocation", netris_id=netris_id)
    if row and row.content_hash == content_hash:
        return True

    obj = nb.find_aggregate(prefix)
    if obj:
        for k, v in body.items():
            if k != "prefix":
                setattr(obj, k, v)
        obj.tags = [{"name": cfg.sync.netris_origin_tag_on_netbox}]
        obj.save()
        action = "updated"
    else:
        create_body = dict(body)
        create_body["tags"] = [{"name": cfg.sync.netris_origin_tag_on_netbox}]
        obj = nb.create_aggregate(**create_body)
        action = "created"

    db.upsert_mapping("netris_import", "aggregate", obj.id, "allocation", netris_id, content_hash)
    logger.info("%s NetBox aggregate %s from Netris allocation %s (%s)", action, obj.id, netris_id, prefix)

    if cfg.sync.enrich_netbox_custom_fields:
        _stamp_enrichment(obj, cfg, netris_id, (allocation.get("vpc") or {}).get("id"))
    return True


def _import_subnet(nb, db, cfg, subnet):
    netris_id = subnet.get("id")
    prefix = subnet.get("prefix")
    if not prefix:
        return False

    sites = subnet.get("sites") or []
    if not sites:
        logger.warning("Skipping Netris subnet %s (%s): no site attached", netris_id, prefix)
        return False
    if len(sites) > 1:
        logger.warning(
            "Netris subnet %s (%s) is attached to multiple sites (%s) - mirroring "
            "against the first one only (%s)",
            netris_id, prefix, [s.get("name") for s in sites], sites[0].get("name"),
        )
    site = nb.get_or_create_site(sites[0]["name"])

    tenant_name = (subnet.get("tenant") or {}).get("name") or "Netris"
    tenant = nb.get_or_create_tenant(tenant_name)

    purpose = subnet.get("purpose") or "common"
    role = nb.get_or_create_role(purpose.replace("-", " ").title())

    body = {
        "prefix": prefix,
        "scope_type": "dcim.site",
        "scope_id": site.id,
        "tenant": tenant.id,
        "role": role.id,
        "status": "active",
        "description": subnet.get("name") or prefix,
    }
    content_hash = _hash(body)

    row = db.get_mapping(direction="netris_import", netris_type="subnet", netris_id=netris_id)
    if row and row.content_hash == content_hash:
        return True

    obj = nb.find_prefix(prefix)
    if obj:
        for k, v in body.items():
            if k != "prefix":
                setattr(obj, k, v)
        obj.tags = [{"name": cfg.sync.netris_origin_tag_on_netbox}]
        obj.save()
        action = "updated"
    else:
        create_body = dict(body)
        create_body["tags"] = [{"name": cfg.sync.netris_origin_tag_on_netbox}]
        obj = nb.create_prefix(**create_body)
        action = "created"

    db.upsert_mapping("netris_import", "prefix", obj.id, "subnet", netris_id, content_hash)
    logger.info("%s NetBox prefix %s from Netris subnet %s (%s)", action, obj.id, netris_id, prefix)

    if cfg.sync.enrich_netbox_custom_fields:
        _stamp_enrichment(obj, cfg, netris_id, (subnet.get("vpc") or {}).get("id"))
    return True


def _stamp_enrichment(obj, cfg, netris_id, vpc_id):
    """Best-effort: writes netris_id (always) and the real Netris VPC (if known) onto a
    freshly created/updated mirrored object, so it's visible in the NetBox UI and so a
    mirrored object that later gets manually re-pushed (Push to Netris? flipped on)
    lands back in the VPC it actually already belongs to."""
    try:
        obj.custom_fields["netris_id"] = str(netris_id)
        if vpc_id is not None:
            obj.custom_fields[cfg.sync.vpc_custom_field] = str(vpc_id)
        obj.save()
    except Exception as exc:
        logger.debug("Could not write enrichment custom fields on NetBox object %s: %s", obj.id, exc)


def _handle_removed(nb, db, cfg, netris_type, seen_ids):
    if cfg.sync.on_netris_subnet_removed != "deprecate":
        return
    for row in db.get_stale_netris_mappings("netris_import", netris_type, seen_ids):
        if row.netbox_type == "aggregate":
            obj = nb.api.ipam.aggregates.get(id=row.netbox_id)
            # Aggregates have no status/lifecycle field - there's no non-destructive
            # "soft" state to move it to, so just flag it and leave it alone.
            if obj:
                logger.warning(
                    "Netris allocation %s (mirrored as NetBox aggregate %s, %s) is no "
                    "longer present in Netris - left as-is, aggregates have no "
                    "deprecated state to move it to",
                    row.netris_id, obj.id, obj.prefix,
                )
        else:
            obj = nb.api.ipam.prefixes.get(id=row.netbox_id)
            if obj and getattr(obj.status, "value", obj.status) != "deprecated":
                obj.status = "deprecated"
                obj.save()
                logger.info(
                    "Deprecated NetBox prefix %s (Netris subnet %s no longer present)",
                    obj.prefix, row.netris_id,
                )
        db.mark_stale(row.id)
