# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {
  name     = "test-1str-1srv-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}

resource "netris_vpc" "storage" {
  name     = "test-1str-1srv-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}
