# -----------------------------------------------------------------------------
# Out-of-Band (OOB) Switch & Management Server Links
# -----------------------------------------------------------------------------

locals {
  links_oob_switch_rows = csvdecode(file("./csv/links_oob_switch.csv"))
  links_oob_switch_map = {
    for idx, row in local.links_oob_switch_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "oob_switch_links" {
  for_each = local.links_oob_switch_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [netris_switch.switches, netris_server.mgmt_servers, netris_server.storage_servers]
}
