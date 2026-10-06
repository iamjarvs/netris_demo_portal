# -----------------------------------------------------------------------------
# GPU Servers from csv/servers_gpu.csv
# -----------------------------------------------------------------------------

locals {
  gpu_servers_rows = csvdecode(file("./csv/servers_gpu.csv"))
  gpu_servers_map = {
    for row in local.gpu_servers_rows :
    row.name => row
  }
}

resource "netris_server" "gpu_servers" {
  for_each    = local.gpu_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
