# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-sonic-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "oob_mgmt" {
  name     = "test-sonic-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-sonic-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
