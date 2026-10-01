# ---------------------------------------------------------------- account

variable "subscription_id" {
  description = "Azure subscription to deploy into."
  type        = string
}

variable "tenant_id" {
  description = "Entra tenant. Null uses the tenant of the current az login."
  type        = string
  default     = null
}

# ---------------------------------------------------------------- naming

variable "project" {
  description = "Short project code used in every resource name."
  type        = string
  default     = "sigpoc"

  validation {
    condition     = can(regex("^[a-z0-9]{2,8}$", var.project))
    error_message = "project must be 2-8 lowercase letters/digits (used in storage, ACR and Key Vault names)."
  }
}

variable "environment" {
  description = "Environment code, e.g. poc, dev."
  type        = string
  default     = "poc"

  validation {
    condition     = can(regex("^[a-z0-9]{2,6}$", var.environment))
    error_message = "environment must be 2-6 lowercase letters/digits."
  }
}

# ---------------------------------------------------------------- regions

variable "location" {
  description = "Main region: app, database, telemetry and SigNoz."
  type        = string
}

variable "location_short" {
  description = "Short code for the main region used in names, e.g. uks."
  type        = string
}

variable "support_location" {
  description = "Region for the Windows support VM (can differ to use a separate vCPU quota)."
  type        = string
}

variable "support_location_short" {
  description = "Short code for the support VM region, e.g. ukw."
  type        = string
}

# ---------------------------------------------------------------- network

variable "vnet_address_space" {
  description = "Main VNet address space."
  type        = string
}

variable "subnet_prefixes" {
  description = "Main VNet subnets."
  type = object({
    bastion           = string # AzureBastionSubnet, /26 or larger
    signoz            = string # SigNoz VM
    app_integration   = string # Web App VNet integration (delegated)
    private_endpoints = string # private endpoints
  })
}

variable "support_vnet_address_space" {
  description = "Support VM VNet address space. Must not overlap the main VNet."
  type        = string
}

variable "support_subnet_prefix" {
  description = "Support VM subnet."
  type        = string
}

# ---------------------------------------------------------------- virtual machines

variable "signoz_vm_size" {
  description = "SigNoz VM size (runs SigNoz + OTel Collector)."
  type        = string
  default     = "Standard_B4as_v2"
}

variable "signoz_vm_private_ip" {
  description = "Static private IP of the SigNoz VM, inside subnet_prefixes.signoz."
  type        = string
}

variable "signoz_vm_disk_size_gb" {
  description = "SigNoz VM OS disk size (ClickHouse data lives here in the POC)."
  type        = number
  default     = 64
}

variable "support_vm_size" {
  description = "Windows support VM size."
  type        = string
  default     = "Standard_B2s_v2"
}

variable "support_vm_private_ip" {
  description = "Static private IP of the support VM, inside support_subnet_prefix."
  type        = string
}

variable "support_vm_admin_username" {
  description = "Windows support VM admin user. Password is generated into Key Vault."
  type        = string
  default     = "dqadmin"
}

variable "enable_support_vm" {
  description = "Create the Windows support VM, its VNet and peering."
  type        = bool
  default     = true
}

variable "auto_shutdown_time" {
  description = "Daily VM auto-shutdown time, HHMM."
  type        = string
  default     = "1900"
}

variable "auto_shutdown_timezone" {
  description = "Windows time zone name for auto-shutdown."
  type        = string
  default     = "India Standard Time"
}

# ---------------------------------------------------------------- bastion

variable "enable_bastion" {
  description = "Create Bastion. Set false and apply to remove it when idle (largest cost line)."
  type        = bool
  default     = true
}

variable "bastion_sku" {
  description = "Bastion SKU. Standard is needed to reach VMs in peered VNets and for native-client tunnels."
  type        = string
  default     = "Standard"
}

# ---------------------------------------------------------------- platform SKUs

variable "app_service_sku" {
  description = "App Service plan SKU. B1 is the smallest with VNet integration and private endpoints."
  type        = string
  default     = "B1"
}

variable "webapp_placeholder_image" {
  description = "Initial container image until the app image is pushed to ACR."
  type = object({
    registry_url = string
    image        = string
    port         = string
  })
  default = {
    registry_url = "https://mcr.microsoft.com"
    image        = "azuredocs/aci-helloworld:latest"
    port         = "80"
  }
}

variable "acr_sku" {
  type    = string
  default = "Basic"
}

variable "sql_admin_login" {
  type    = string
  default = "dqadmin"
}

variable "sql_database_name" {
  type    = string
  default = "sqldb-dqlite"
}

variable "sql_sku" {
  description = "Azure SQL database SKU."
  type        = string
  default     = "Basic"
}

variable "sql_max_size_gb" {
  type    = number
  default = 2
}

variable "eventhub_sku" {
  description = "Event Hub namespace SKU. Standard or higher is needed for private endpoints."
  type        = string
  default     = "Standard"
}

variable "eventhub_partition_count" {
  type    = number
  default = 2
}

variable "eventhub_retention_days" {
  type    = number
  default = 1
}

variable "storage_replication_type" {
  type    = string
  default = "LRS"
}

variable "app_logs_container_name" {
  description = "Blob container for plain-text app logs."
  type        = string
  default     = "app-logs"
}

variable "key_vault_public_access" {
  description = "Keep Key Vault's public endpoint (RBAC-protected) so Terraform outside the VNet can write secrets."
  type        = bool
  default     = true
}

# ---------------------------------------------------------------- tags

variable "owner" {
  description = "Owner tag."
  type        = string
}

variable "expiry" {
  description = "Expiry date tag (YYYY-MM-DD) for clean-up."
  type        = string
}

variable "extra_tags" {
  description = "Additional tags merged onto every resource."
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------- application (Phase 2)

variable "app_image" {
  description = "App image in this deployment's ACR, e.g. dqlite-api:v1. Null keeps the Phase 1 placeholder."
  type        = string
  default     = null
}

variable "app_port" {
  description = "Port the app container listens on."
  type        = string
  default     = "8080"
}

variable "app_test_endpoints_enabled" {
  description = "Enable /api/test/* fault-injection endpoints."
  type        = bool
  default     = true
}

variable "otel_service_name" {
  description = "OpenTelemetry service.name for the app."
  type        = string
  default     = "dqlite-api"
}

variable "otel_tenant" {
  description = "tenant.id resource attribute (tenant separation in SigNoz)."
  type        = string
  default     = "demo"
}
