locals {
  # {type}-{project}-{environment}-{region}, e.g. vm-signoz-sigpoc-poc-cin
  name_base         = "${var.project}-${var.environment}-${var.location_short}"
  support_name_base = "${var.project}-${var.environment}-${var.support_location_short}"

  # Short random suffix for globally unique names (storage, Key Vault, ACR, SQL, Web App, Event Hub).
  suffix = random_string.suffix.result

  names = {
    resource_group    = "rg-${local.name_base}"
    vnet              = "vnet-${local.name_base}"
    nsg_signoz        = "nsg-signoz-${local.name_base}"
    bastion           = "bas-${local.name_base}"
    bastion_pip       = "pip-bas-${local.name_base}"
    signoz_vm         = "vm-signoz-${local.name_base}"
    signoz_nic        = "nic-vm-signoz-${local.name_base}"
    support_vnet      = "vnet-${local.support_name_base}"
    support_nsg       = "nsg-support-${local.support_name_base}"
    support_vm        = "vm-support-${local.support_name_base}"
    support_nic       = "nic-vm-support-${local.support_name_base}"
    app_service_plan  = "asp-${local.name_base}"
    webapp            = "app-dqlite-${local.name_base}-${local.suffix}"
    acr               = "cr${var.project}${var.environment}${local.suffix}"
    sql_server        = "sql-${local.name_base}-${local.suffix}"
    storage_account   = "st${var.project}${var.environment}${local.suffix}"
    key_vault         = "kv-${var.project}-${var.environment}-${local.suffix}"
    eventhub_ns       = "evhns-${local.name_base}-${local.suffix}"
    eventhub          = "platform-logs"
    eventhub_consumer = "otelcol"
  }

  tags = merge({
    project     = var.project
    environment = var.environment
    owner       = var.owner
    expiry      = var.expiry
    managed-by  = "terraform"
  }, var.extra_tags)
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = local.names.resource_group
  location = var.location
  tags     = local.tags
}
