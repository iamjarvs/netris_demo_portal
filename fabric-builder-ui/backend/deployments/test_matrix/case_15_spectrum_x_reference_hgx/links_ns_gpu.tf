# -----------------------------------------------------------------------------
# North-South Leaf to GPU Management Links
# -----------------------------------------------------------------------------

locals {
  links_ns_gpu_rows = csvdecode(file("./csv/links_ns_gpu.csv"))
  links_ns_gpu_map = {
    for idx, row in local.links_ns_gpu_rows :
    "${row.leaf_port}@${row.leaf}--${row.gpu_port}@${row.gpu}" => row
  }
}

resource "netris_link" "ns_gpu_links" {
  for_each = local.links_ns_gpu_map

  ports = [
    "${each.value.leaf_port}@${each.value.leaf}",
    "${each.value.gpu_port}@${each.value.gpu}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_server.gpu_servers
  ]
}
