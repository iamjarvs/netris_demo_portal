# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-qp-8roce-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}
