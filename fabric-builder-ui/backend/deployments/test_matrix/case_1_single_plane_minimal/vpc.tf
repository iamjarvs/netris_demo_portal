# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-sp-min-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
