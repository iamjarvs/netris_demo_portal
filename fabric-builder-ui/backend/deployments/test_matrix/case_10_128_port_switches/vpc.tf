# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-128p-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "oob_mgmt" {
  name     = "test-128p-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-128p-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
