# -----------------------------------------------------------------------------
# Inventory Profiles
# -----------------------------------------------------------------------------

resource "netris_inventory_profile" "ns_profile" {
  name        = "egg-ns-profile"
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
  name        = "egg-ew-pl1"
  description = "East-West Spectrum-X Profile for Plane 1"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = false
    unnumberedbgpunderlay    = true
    optimisebgpoverlay       = true
    fabrictype               = "ew-plane1"
  }

  gpuclustersettings {
    congestioncontrol    = true
    qosandroce           = true
    roceadaptiverouting  = true
    aggregatel3vpnprefix = true
    refarch              = "b300_spx_2_tier_quad_plane"
  }
}

resource "netris_inventory_profile" "ew_profile_pl2" {
  name        = "egg-ew-pl2"
  description = "East-West Spectrum-X Profile for Plane 2"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = false
    unnumberedbgpunderlay    = true
    optimisebgpoverlay       = true
    fabrictype               = "ew-plane2"
  }

  gpuclustersettings {
    congestioncontrol    = true
    qosandroce           = true
    roceadaptiverouting  = true
    aggregatel3vpnprefix = true
    refarch              = "b300_spx_2_tier_quad_plane"
  }
}

resource "netris_inventory_profile" "ew_profile_pl3" {
  name        = "egg-ew-pl3"
  description = "East-West Spectrum-X Profile for Plane 3"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = false
    unnumberedbgpunderlay    = true
    optimisebgpoverlay       = true
    fabrictype               = "ew-plane3"
  }

  gpuclustersettings {
    congestioncontrol    = true
    qosandroce           = true
    roceadaptiverouting  = true
    aggregatel3vpnprefix = true
    refarch              = "b300_spx_2_tier_quad_plane"
  }
}

resource "netris_inventory_profile" "ew_profile_pl4" {
  name        = "egg-ew-pl4"
  description = "East-West Spectrum-X Profile for Plane 4"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    automaticlinkaggregation = false
    unnumberedbgpunderlay    = true
    optimisebgpoverlay       = true
    fabrictype               = "ew-plane4"
  }

  gpuclustersettings {
    congestioncontrol    = true
    qosandroce           = true
    roceadaptiverouting  = true
    aggregatel3vpnprefix = true
    refarch              = "b300_spx_2_tier_quad_plane"
  }
}

resource "netris_inventory_profile" "oob_profile" {
  name        = "egg-oob-profile"
  description = "Out-of-band management profile"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {
    fabrictype = "oob"
  }
}

