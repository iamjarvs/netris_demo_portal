"""Keeps the "Netris VPC" NetBox custom field's dropdown options in sync with the
VPCs that actually exist in Netris (GET /api/v2/vpc), so it's never just hard-coded
to one VPC and never goes stale as VPCs are added/renamed in Netris. Runs every
Netris->NetBox poll cycle - cheap (two small API calls) and keeps the picker current
without needing a service restart.
"""
import logging

logger = logging.getLogger(__name__)


def sync_vpc_choices(nb, netris, cfg):
    vpcs = netris.list_vpcs()
    extra_choices = [[str(v["id"]), f"{v['name']} (id {v['id']})"] for v in vpcs if v.get("id")]
    extra_choices.sort(key=lambda pair: pair[1].lower())

    choice_set_name = f"{cfg.sync.vpc_custom_field}-choices"
    choice_set = nb.get_or_create_choice_set(choice_set_name, extra_choices)

    changed = nb.update_choice_set(choice_set, extra_choices)
    if changed:
        logger.info("Refreshed Netris VPC choices (%d VPCs)", len(extra_choices))

    return choice_set
