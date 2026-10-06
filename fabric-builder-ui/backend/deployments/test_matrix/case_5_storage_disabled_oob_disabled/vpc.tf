# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-no-opt-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
