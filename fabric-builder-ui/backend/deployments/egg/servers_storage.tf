# -----------------------------------------------------------------------------
# Storage Servers from csv/servers_storage.csv
# -----------------------------------------------------------------------------

locals {
  storage_servers_rows = csvdecode(file("./csv/servers_storage.csv"))
  storage_servers_map = {
    for row in local.storage_servers_rows :
    row.name => row
  }
}

resource "netris_server" "storage_servers" {
  for_each    = local.storage_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
