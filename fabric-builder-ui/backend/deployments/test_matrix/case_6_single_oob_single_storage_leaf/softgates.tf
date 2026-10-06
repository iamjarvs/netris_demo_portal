# -----------------------------------------------------------------------------
# Softgates — Border Gateway / NAT nodes from csv/softgates.csv
# -----------------------------------------------------------------------------

locals {
  softgates_rows = csvdecode(file("./csv/softgates.csv"))
  softgates_map = {
    for row in local.softgates_rows :
    row.index => row
  }
}

resource "netris_softgate" "softgates" {
  for_each    = local.softgates_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  mainip      = each.value.mainip
  mgmtip      = each.value.mgmtip
  flavor      = var.softgate_flavor
  role        = each.value.role
  profileid   = netris_inventory_profile.ns_profile.id

  depends_on = [
    netris_site.site,
    netris_subnet.subnets,
    netris_inventory_profile.ns_profile
  ]
}
