# -----------------------------------------------------------------------------
# Switches — loaded from csv/switches.csv
# -----------------------------------------------------------------------------

locals {
  switches_rows = csvdecode(file("./csv/switches.csv"))
  switches_map = {
    for row in local.switches_rows :
    row.index => row
  }

  switch_profile_ids = {
    "ew_profile_pl1" = netris_inventory_profile.ew_profile_pl1.id
    "ew_profile_pl2" = netris_inventory_profile.ew_profile_pl2.id
    "ew_profile_pl3" = netris_inventory_profile.ew_profile_pl3.id
    "ew_profile_pl4" = netris_inventory_profile.ew_profile_pl4.id
    "ns_profile"     = netris_inventory_profile.ns_profile.id
  }
}

resource "netris_switch" "switches" {
  for_each    = local.switches_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  nos         = var.nos
  asnumber    = each.value.asn
  profileid   = local.switch_profile_ids[each.value.profile]
  portcount   = each.value.portcount
  mainip      = each.value.loopback
  mgmtip      = each.value.mgmtip
  role        = each.value.role

  depends_on = [
    netris_site.site,
    netris_subnet.subnets,
    netris_inventory_profile.ns_profile
  ]
}
