# -----------------------------------------------------------------------------
# IPAM: Allocations and Subnets via csv/ipam.csv
# -----------------------------------------------------------------------------

locals {
  ipam_rows = csvdecode(file("./csv/ipam.csv"))
  allocations = {
    for row in local.ipam_rows :
    row.name => row if row.type == "allocation"
  }
  subnets = {
    for row in local.ipam_rows :
    row.name => row if row.type == "subnet"
  }
}

resource "netris_allocation" "allocations" {
  for_each = local.allocations
  name     = each.value.name
  prefix   = each.value.prefix
  tenantid = data.netris_tenant.admin.id

  depends_on = [netris_site.site]
}

resource "netris_subnet" "subnets" {
  for_each       = local.subnets
  name           = each.value.name
  prefix         = each.value.prefix
  purpose        = each.value.purpose
  defaultgateway = each.value.default_gateway != "" ? each.value.default_gateway : null
  tenantid       = data.netris_tenant.admin.id
  siteids        = [netris_site.site.id]

  depends_on = [
    netris_allocation.allocations,
    netris_site.site
  ]
}
