# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-1gpu-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
