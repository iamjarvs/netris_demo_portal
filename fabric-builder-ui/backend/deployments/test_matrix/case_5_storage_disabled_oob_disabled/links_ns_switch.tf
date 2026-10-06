# -----------------------------------------------------------------------------
# North-South Spine-Leaf Links
# -----------------------------------------------------------------------------

locals {
  links_ns_switch_rows = csvdecode(file("./csv/links_ns_switch.csv"))
  links_ns_switch_map = {
    for idx, row in local.links_ns_switch_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "ns_switch_links" {
  for_each = local.links_ns_switch_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [netris_switch.switches]
}
