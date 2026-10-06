# -----------------------------------------------------------------------------
# Softgate to Border/NS Leaf Links
# -----------------------------------------------------------------------------

locals {
  links_softgate_rows = csvdecode(file("./csv/links_softgate.csv"))
  links_softgate_map = {
    for idx, row in local.links_softgate_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "softgate_links" {
  for_each = local.links_softgate_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_softgate.softgates
  ]
}
