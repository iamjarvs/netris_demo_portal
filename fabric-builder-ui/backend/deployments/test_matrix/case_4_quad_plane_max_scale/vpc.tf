# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-qp-max-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "oob_mgmt" {
  name     = "test-qp-max-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-qp-max-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
