"""NetBox -> Netris: push Prefixes/Aggregates checked "Push to Netris?" as Netris
Subnets/Allocations.

Opt-in is a boolean NetBox custom field (sync.push_custom_field, "push_to_netris" by
default) rather than a tag - a checkbox on the object's edit form is far more
discoverable than a magic tag name, and NetBox's `cf_<name>=true` REST filter makes
querying for it just as cheap. Which Netris VPC to land in is a second custom field
(sync.vpc_custom_field, "netris_vpc") - a dropdown whose options are the real VPCs
in Netris (see vpc_choices.py), not hard-coded to Default.

NetBox is the planning source of truth here, so this direction only ever creates or
updates in Netris - it never deletes on its own initiative. If a previously-synced
prefix is un-checked or removed in NetBox, it's flagged for manual review instead
(see config: on_netbox_prefix_removed) rather than auto-deleting a subnet a live
cluster might still be using.

The one place this module DOES delete something in Netris is moving an
already-pushed object to a different VPC - Netris silently ignores a "vpc" change on
PUT (returns 200, never actually moves it - verified empirically), so the only way
to really move one is delete the old object and create a new one in the target VPC.

**This must always be create-first, delete-second, never the reverse.** An earlier
version of this deleted the old object immediately on detecting a VPC mismatch, then
tried to create the replacement - and when that create failed (e.g. no allocation
exists yet in the target VPC, a real Netris containment rule), the result was a
real Netris subnet permanently destroyed with nothing to replace it, on a live
customer's controller. Every VPC-move path below creates and confirms the
replacement's id first; the old object is only ever deleted in the line right after
that confirmation succeeds. If create fails or returns no id, the function returns
early and the original object is left completely untouched.
"""
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def _hash(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _extract_id(result):
    """Netris's create/update responses wrap the id as {"data": {"id": ...}}, not the
    flat {"id": ...} the OpenAPI spec for these endpoints actually documents -
    verified empirically against a live controller. Handle both shapes defensively
    rather than assume one."""
    if not result:
        return None
    if "id" in result:
        return result["id"]
    data = result.get("data")
    if isinstance(data, dict):
        return data.get("id")
    return None


def _resolve_site(nb, cfg, obj):
    """NetBox 4.2+ replaced Prefix.site with a generic scope (scope_type/scope_id) that
    can point at a Site, Region, SiteGroup, or Location. We only support Site-scoped
    prefixes for now. The nested `scope` object pynetbox returns doesn't reliably carry
    a slug (it's a generic serializer), so we fetch the real Site by id instead of
    guessing at its shape.
    """
    scope_type = getattr(obj, "scope_type", None)
    scope = getattr(obj, "scope", None)
    if not scope_type or not scope:
        return None
    if str(scope_type) != "dcim.site":
        logger.warning(
            "Prefix %s is scoped to %r, not a Site - only Site-scoped prefixes are supported",
            obj.id, scope_type,
        )
        return None
    site = nb.get_site(scope.id)
    if not site:
        return None
    return cfg.mapping.sites.get(site.slug)


def _resolve_tenant(cfg, obj):
    """Netris genuinely requires a tenant on every allocation/subnet (confirmed
    empirically - it 403s "Must have required property 'tenant'" without one, this
    isn't optional). If the NetBox tenant isn't explicitly mapped, fall back to
    mapping.default_tenant_id when configured, rather than skip."""
    tenant_slug = getattr(getattr(obj, "tenant", None), "slug", None)
    mapped = cfg.mapping.tenants.get(tenant_slug) if tenant_slug else None
    if mapped is not None:
        return mapped
    return cfg.mapping.default_tenant_id


def _find_tree_node(nodes, target_id, target_type):
    """Netris allocations and subnets do NOT share a single id sequence - verified
    empirically that a subnet and an allocation can have the same numeric id (e.g. a
    real subnet id=60 turned up nested elsewhere in the very same tree as allocation
    id=60). Matching on id alone silently returns whichever one the depth-first walk
    hits first, which can be the wrong object entirely. Always match type too."""
    for node in nodes:
        if node.get("id") == target_id and node.get("type") == target_type:
            return node
        found = _find_tree_node(node.get("children") or [], target_id, target_type)
        if found:
            return found
    return None


def _live_vpc_and_children(netris, netris_id, netris_type):
    """Reads Netris directly for an already-linked object's *actual* current VPC and
    whether it has children, rather than trusting our own DB's historical vpc_id.

    This matters: Netris silently ignores a "vpc" change on PUT (returns 200, never
    moves the object - verified empirically), so an object can already be sitting in
    the wrong VPC from a no-op update that happened before this check existed. Comparing
    against our own prior recorded vpc_id would miss that case entirely the first time
    (nothing "changed" from our DB's point of view). Ground truth is the only thing that
    can't be silently stale like that.

    Netris also cascade-deletes children (subnets, and any hosts under them) when their
    parent allocation/subnet is deleted - verified empirically - so callers need
    `has_children` to decide whether an automatic delete is safe.
    """
    vpc_ids = [v["id"] for v in netris.list_vpcs() if v.get("id")]
    tree = netris.get_ipam_tree(vpc_ids=vpc_ids)
    node = _find_tree_node(tree, netris_id, netris_type)
    if node is None:
        return None, False
    current_vpc_id = (node.get("vpc") or {}).get("id")
    has_children = bool(node.get("children")) or bool(node.get("hostsCount"))
    return current_vpc_id, has_children


def _resolve_vpc(cfg, obj):
    """Reads the "Netris VPC" select custom field (vpc_choices.py keeps its dropdown
    populated with real Netris VPCs). NetBox returns a select field's value as
    {"value": ..., "label": ...} once set - handle a bare string too, defensively.
    Returns None (meaning: let Netris default to its Default VPC) if unset."""
    raw = (obj.custom_fields or {}).get(cfg.sync.vpc_custom_field)
    if not raw:
        return None
    value = raw.get("value") if isinstance(raw, dict) else raw
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Could not parse Netris VPC custom field value %r on object %s", raw, obj.id)
        return None


def push_netbox_to_netris(nb, netris, db, cfg):
    field_name = cfg.sync.push_custom_field
    aggregates = nb.aggregates_flagged_for_push(field_name)
    prefixes = nb.prefixes_flagged_for_push(field_name)

    seen_aggregate_ids = set()
    for agg in aggregates:
        try:
            if _sync_aggregate(nb, netris, db, cfg, agg):
                seen_aggregate_ids.add(agg.id)
        except Exception:
            logger.exception("Failed to sync NetBox aggregate %s (%s)", agg.id, agg.prefix)

    seen_prefix_ids = set()
    for pfx in prefixes:
        try:
            if _sync_prefix(nb, netris, db, cfg, pfx):
                seen_prefix_ids.add(pfx.id)
        except Exception:
            logger.exception("Failed to sync NetBox prefix %s (%s)", pfx.id, pfx.prefix)

    _flag_removed(db, cfg, "aggregate", seen_aggregate_ids)
    _flag_removed(db, cfg, "prefix", seen_prefix_ids)


def _sync_aggregate(nb, netris, db, cfg, obj):
    netbox_id = obj.id
    prefix = str(obj.prefix)

    tenant_id = _resolve_tenant(cfg, obj)
    if tenant_id is None:
        logger.warning(
            "Skipping aggregate %s (%s): no Netris tenant mapping for NetBox tenant %r",
            netbox_id, prefix, getattr(getattr(obj, "tenant", None), "slug", None),
        )
        return False

    body = {"name": obj.description or prefix, "tenant": {"id": tenant_id}, "prefix": prefix}
    vpc_id = _resolve_vpc(cfg, obj)
    if vpc_id is not None:
        body["vpc"] = {"id": vpc_id}
    content_hash = _hash(body)

    row = db.get_mapping(direction="netbox_to_netris", netbox_type="aggregate", netbox_id=netbox_id)

    # netris_id of the old allocation to remove, but ONLY after its replacement has
    # been confirmed to actually exist - see the module-level note on why this must
    # never be delete-then-create.
    retire_id = None

    if row and row.netris_id and vpc_id is not None:
        live_vpc_id, has_children = _live_vpc_and_children(netris, row.netris_id, "allocation")
        if live_vpc_id is not None and live_vpc_id != vpc_id:
            if has_children:
                logger.error(
                    "Aggregate %s (%s): wants Netris VPC %s but allocation %s is "
                    "actually still in VPC %s and has child subnets/hosts in Netris - "
                    "refusing to auto-move it (that would cascade-delete them). "
                    "Remove/move its children first, or leave the VPC as it was.",
                    netbox_id, prefix, vpc_id, row.netris_id, live_vpc_id,
                )
                return False
            logger.warning(
                "Aggregate %s (%s): wants Netris VPC %s but allocation %s is actually "
                "still in VPC %s - Netris does not support moving an existing "
                "allocation between VPCs. Will create a fresh allocation in the new "
                "VPC first, and only remove %s once that succeeds.",
                netbox_id, prefix, vpc_id, row.netris_id, live_vpc_id, row.netris_id,
            )
            retire_id = row.netris_id
            row = None  # force the create path below - nothing in Netris touched yet

    if row and row.content_hash == content_hash:
        return True

    if row and row.netris_id:
        netris.update_allocation(row.netris_id, body)
        netris_id, action = row.netris_id, "updated"
    else:
        result = netris.create_allocation(body)
        netris_id = _extract_id(result)
        if netris_id is None:
            logger.error(
                "Aggregate %s (%s): create_allocation returned no id (response: %r) - "
                "not touching allocation %s, nothing to fall back to otherwise",
                netbox_id, prefix, result, retire_id,
            )
            return False
        action = "created"
        if retire_id is not None:
            logger.info(
                "Aggregate %s (%s): new allocation %s confirmed created in VPC %s - "
                "removing old allocation %s now",
                netbox_id, prefix, netris_id, vpc_id, retire_id,
            )
            try:
                netris.delete_allocation(retire_id)
            except Exception:
                logger.exception(
                    "Aggregate %s (%s): created new allocation %s but failed to "
                    "delete old allocation %s - both now exist in Netris, needs manual "
                    "cleanup",
                    netbox_id, prefix, netris_id, retire_id,
                )

    db.upsert_mapping(
        "netbox_to_netris", "aggregate", netbox_id, "allocation", netris_id, content_hash, vpc_id=vpc_id
    )
    logger.info("%s Netris allocation %s from NetBox aggregate %s (%s)", action, netris_id, netbox_id, prefix)
    return True


def _sync_prefix(nb, netris, db, cfg, obj):
    netbox_id = obj.id
    prefix = str(obj.prefix)

    tenant_id = _resolve_tenant(cfg, obj)
    if tenant_id is None:
        logger.warning(
            "Skipping prefix %s (%s): no Netris tenant mapping for NetBox tenant %r",
            netbox_id, prefix, getattr(getattr(obj, "tenant", None), "slug", None),
        )
        return False

    site_id = _resolve_site(nb, cfg, obj)
    if site_id is None:
        logger.warning(
            "Skipping prefix %s (%s): no Netris site mapping for NetBox scope %r/%r "
            "(is it Site-scoped, and is that site listed in config.yaml mapping.sites?)",
            netbox_id, prefix, getattr(obj, "scope_type", None), getattr(obj, "scope", None),
        )
        return False

    role_slug = getattr(getattr(obj, "role", None), "slug", None)
    purpose = cfg.role_to_purpose.get(role_slug, "common")

    body = {
        "name": obj.description or prefix,
        "tenant": {"id": tenant_id},
        "sites": [{"id": site_id}],
        "purpose": purpose,
        "prefix": prefix,
        "tags": [cfg.sync.netbox_origin_tag_on_netris],
    }
    vpc_id = _resolve_vpc(cfg, obj)
    if vpc_id is not None:
        body["vpc"] = {"id": vpc_id}
    content_hash = _hash(body)

    row = db.get_mapping(direction="netbox_to_netris", netbox_type="prefix", netbox_id=netbox_id)

    # netris_id of the old subnet to remove, but ONLY after its replacement has been
    # confirmed to actually exist - see the module-level note on why this must never
    # be delete-then-create.
    retire_id = None

    if row and row.netris_id and vpc_id is not None:
        live_vpc_id, has_children = _live_vpc_and_children(netris, row.netris_id, "subnet")
        if live_vpc_id is not None and live_vpc_id != vpc_id:
            if has_children:
                logger.error(
                    "Prefix %s (%s): wants Netris VPC %s but subnet %s is actually "
                    "still in VPC %s and has hosts assigned in Netris - refusing to "
                    "auto-move it (that would cascade-delete those reservations). "
                    "Free them first, or leave the VPC as it was.",
                    netbox_id, prefix, vpc_id, row.netris_id, live_vpc_id,
                )
                return False
            logger.warning(
                "Prefix %s (%s): wants Netris VPC %s but subnet %s is actually still "
                "in VPC %s - Netris does not support moving an existing subnet "
                "between VPCs. Will create a fresh subnet in the new VPC first (which "
                "requires an allocation already covering this range in that VPC), and "
                "only remove %s once that succeeds.",
                netbox_id, prefix, vpc_id, row.netris_id, live_vpc_id, row.netris_id,
            )
            retire_id = row.netris_id
            row = None  # force the create path below - nothing in Netris touched yet

    if row and row.content_hash == content_hash:
        return True

    if row and row.netris_id:
        netris.update_subnet(row.netris_id, body)
        netris_id, action = row.netris_id, "updated"
    else:
        result = netris.create_subnet(body)
        netris_id = _extract_id(result)
        if netris_id is None:
            logger.error(
                "Prefix %s (%s): create_subnet returned no id (response: %r) - not "
                "touching subnet %s, nothing to fall back to otherwise",
                netbox_id, prefix, result, retire_id,
            )
            return False
        action = "created"
        if retire_id is not None:
            logger.info(
                "Prefix %s (%s): new subnet %s confirmed created in VPC %s - removing "
                "old subnet %s now",
                netbox_id, prefix, netris_id, vpc_id, retire_id,
            )
            try:
                netris.delete_subnet(retire_id)
            except Exception:
                logger.exception(
                    "Prefix %s (%s): created new subnet %s but failed to delete old "
                    "subnet %s - both now exist in Netris, needs manual cleanup",
                    netbox_id, prefix, netris_id, retire_id,
                )

    db.upsert_mapping(
        "netbox_to_netris", "prefix", netbox_id, "subnet", netris_id, content_hash, vpc_id=vpc_id
    )
    logger.info("%s Netris subnet %s from NetBox prefix %s (%s)", action, netris_id, netbox_id, prefix)

    if cfg.sync.enrich_netbox_custom_fields and netris_id:
        try:
            obj.custom_fields["netris_id"] = str(netris_id)
            obj.save()
        except Exception as exc:
            logger.debug("Could not write netris_id custom field on NetBox prefix %s: %s", netbox_id, exc)
    return True


def _flag_removed(db, cfg, netbox_type, seen_ids):
    """Anything we've previously pushed that's no longer flagged for push in NetBox gets
    flagged for manual review - see the module docstring for why this doesn't auto-delete.
    """
    if cfg.sync.on_netbox_prefix_removed != "flag_for_review":
        return  # delete_in_netris not implemented in v1 - deliberately conservative
    for row in db.get_stale_push_mappings(netbox_type, seen_ids):
        db.flag_for_review(row.id)
        logger.warning(
            "NetBox %s %s (Netris %s %s) is no longer flagged for push in NetBox - "
            "flagged for manual review, not auto-deleted from Netris",
            netbox_type, row.netbox_id, row.netris_type, row.netris_id,
        )
