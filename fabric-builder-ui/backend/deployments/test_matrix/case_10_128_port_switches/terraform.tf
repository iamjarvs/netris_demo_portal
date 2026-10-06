# -----------------------------------------------------------------------------
# Terraform Configuration — Netris Multi-Plane Fabric Day-0
# Site: TEST-128P | Backend Planes: 2
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    netris = {
      source  = "netrisai/netris"
      version = ">= 3.6.20, < 4.0.0"
    }
  }
  required_version = ">= 1.7"
}

provider "netris" {
  address  = var.controller_address
  login    = var.controller_login
  password = var.controller_password
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "controller_address" {
  type        = string
  description = "URL for Netris controller (e.g. https://adam-ctl.netris.io)"
}

variable "controller_login" {
  type        = string
  default     = "netris"
  description = "Admin login username"
}

variable "controller_password" {
  type        = string
  description = "Admin login password"
  sensitive   = true
}

variable "site_name" {
  type        = string
  default     = "TEST-128P"
  description = "Datacenter site identifier"
}

variable "public_asn" {
  type        = number
  default     = 65500
  description = "Public BGP ASN for the site"
}

variable "nos" {
  type        = string
  default     = "cumulus_nvue"
  description = "Network Operating System on switches"
}

variable "softgate_flavor" {
  type        = string
  default     = "sg-hs"
  description = "Softgate flavor/profile"
}

variable "tenant_name" {
  type        = string
  default     = "Admin"
  description = "Target administrative tenant"
}

variable "inventory_profile_timezone" {
  type        = string
  default     = "Etc/GMT"
  description = "Timezone for inventory profiles"
}

variable "ntp_servers" {
  type        = list(string)
  default     = ["1.pool.ntp.org", "2.pool.ntp.org"]
  description = "NTP servers"
}

variable "dns_servers" {
  type        = list(string)
  default     = ["1.1.1.1", "8.8.8.8"]
  description = "DNS servers"
}

variable "acl_default_policy" {
  type        = string
  default     = "permit"
  description = "Default policy for undeclared traffic (permit or deny)"
}

variable "vlan_range" {
  type        = string
  default     = "2-4094"
  description = "Total VLAN allocation range for site"
}

variable "vlan_range_auto_assign" {
  type        = string
  default     = "2-3999"
  description = "Auto-assignable VLAN range"
}

# -----------------------------------------------------------------------------
# Data Sources & Site Resource
# -----------------------------------------------------------------------------

data "netris_tenant" "admin" {
  name = var.tenant_name
}

resource "netris_site" "site" {
  name                = var.site_name
  publicasn           = var.public_asn
  acldefaultpolicy    = var.acl_default_policy
  vlanrange           = var.vlan_range
  vlanrangeautoassign = var.vlan_range_auto_assign
}
