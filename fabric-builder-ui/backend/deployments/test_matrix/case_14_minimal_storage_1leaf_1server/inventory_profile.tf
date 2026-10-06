# -----------------------------------------------------------------------------
# Inventory Profiles
# -----------------------------------------------------------------------------

resource "netris_inventory_profile" "ns_profile" {
  name        = "test-1str-1srv-ns-profile"
  description = "North-South Front-End Inventory Profile"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = true
    fabrictype               = "ns"
  }
}

resource "netris_inventory_profile" "ew_profile_pl1" {
  name        = "test-1str-1srv-ew-pl1"
  description = "East-West Spectrum-X Profile for Plane 1"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = false
    unnumberedbgpunderlay    = true
    optimisebgpoverlay       = true
    fabrictype               = "ew"
  }

  gpuclustersettings {
    congestioncontrol    = true
    qosandroce           = true
    roceadaptiverouting  = true
    aggregatel3vpnprefix = true
    refarch              = "b300_spx_2_tier_single_plane"
  }
}

