# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-1oob-1str-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "oob_mgmt" {
  name     = "test-1oob-1str-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-1oob-1str-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
