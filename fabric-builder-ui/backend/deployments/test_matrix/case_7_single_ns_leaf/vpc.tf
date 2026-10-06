# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-1ns-lf-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
