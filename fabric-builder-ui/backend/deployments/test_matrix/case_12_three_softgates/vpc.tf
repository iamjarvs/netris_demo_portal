# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-3sg-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
