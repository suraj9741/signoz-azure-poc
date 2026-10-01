# POC: main stack in Central India, Windows support VM in South India (separate vCPU quota).
# UK South hit free-trial capacity/SQL/App Service restrictions (see poc-uksouth.tfvars).

subscription_id = "<your-subscription-id>"

project     = "sigpoc"
environment = "poc"

location               = "centralindia"
location_short         = "cin"
support_location       = "southindia"
support_location_short = "sin"

vnet_address_space = "10.20.0.0/16"
subnet_prefixes = {
  bastion           = "10.20.0.0/26"
  signoz            = "10.20.1.0/24"
  app_integration   = "10.20.2.0/26"
  private_endpoints = "10.20.3.0/27"
}
support_vnet_address_space = "10.30.0.0/16"
support_subnet_prefix      = "10.30.1.0/24"

signoz_vm_size        = "Standard_B4as_v2" # 4 vCPU / 16 GB
signoz_vm_private_ip  = "10.20.1.10"
support_vm_size       = "Standard_B2s_v2" # 2 vCPU / 8 GB
support_vm_private_ip = "10.30.1.10"

enable_bastion    = true
enable_support_vm = true

auto_shutdown_time     = "1900"
auto_shutdown_timezone = "India Standard Time"

owner  = "<owner>"
expiry = "2026-10-03"

# Phase 2: set after `az acr build` pushes the image, then apply.
app_image = "dqlite-api:v1"
