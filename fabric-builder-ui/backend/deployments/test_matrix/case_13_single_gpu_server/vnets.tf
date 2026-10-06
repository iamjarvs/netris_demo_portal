# -----------------------------------------------------------------------------
# Virtual Networks (V-Nets) from csv/vnets.csv
# -----------------------------------------------------------------------------

locals {
  vnets_rows = csvdecode(file("./csv/vnets.csv"))
  vnets_map = {
    for row in local.vnets_rows :
    row.name => row
  }
}

resource "netris_vnet" "vnets" {
  for_each = local.vnets_map
  name     = each.value.name
  tenantid = data.netris_tenant.admin.id
  state    = "active"
  vlanid   = each.value.vlan

  sites {
    id = netris_site.site.id
  }

  depends_on = [
    netris_site.site,
    netris_subnet.subnets
  ]
}
