# -----------------------------------------------------------------------------
# Storage Server Links
# -----------------------------------------------------------------------------

locals {
  links_storage_rows = csvdecode(file("./csv/links_storage.csv"))
  links_storage_map = {
    for idx, row in local.links_storage_rows :
    "${row.leaf_port}@${row.leaf}--${row.server_port}@${row.server}" => row
  }
}

resource "netris_link" "storage_links" {
  for_each = local.links_storage_map

  ports = [
    "${each.value.leaf_port}@${each.value.leaf}",
    "${each.value.server_port}@${each.value.server}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_server.storage_servers
  ]
}
