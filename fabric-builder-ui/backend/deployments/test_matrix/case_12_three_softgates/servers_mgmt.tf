# -----------------------------------------------------------------------------
# Management / CPU Servers from csv/servers_mgmt.csv
# -----------------------------------------------------------------------------

locals {
  mgmt_servers_rows = csvdecode(file("./csv/servers_mgmt.csv"))
  mgmt_servers_map = {
    for row in local.mgmt_servers_rows :
    row.name => row
  }
}

resource "netris_server" "mgmt_servers" {
  for_each    = local.mgmt_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
