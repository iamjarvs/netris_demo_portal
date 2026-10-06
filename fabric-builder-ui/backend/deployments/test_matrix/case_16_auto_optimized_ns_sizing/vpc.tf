# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-auto-ns-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "oob_mgmt" {
  name     = "test-auto-ns-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-auto-ns-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
