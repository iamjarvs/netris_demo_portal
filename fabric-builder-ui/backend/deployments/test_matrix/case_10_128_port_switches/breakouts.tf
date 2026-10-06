# -----------------------------------------------------------------------------
# Port Breakouts (Optional)
# -----------------------------------------------------------------------------

locals {
  breakouts_rows = csvdecode(file("./csv/breakouts.csv"))
  breakouts_map = {
    for idx, row in local.breakouts_rows :
    "${row.port}@${row.switch}" => row
  }
}
