locals {
  webapp_principal_id    = azurerm_linux_web_app.api.identity[0].principal_id
  signoz_vm_principal_id = azurerm_linux_virtual_machine.signoz.identity[0].principal_id
  runner_principal_id    = data.azurerm_client_config.current.object_id
}

# ---------------------------------------------------------------- Terraform runner

resource "azurerm_role_assignment" "runner_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = local.runner_principal_id
}

resource "azurerm_role_assignment" "runner_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.runner_principal_id
}

# ---------------------------------------------------------------- Web App managed identity

resource "azurerm_role_assignment" "webapp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = local.webapp_principal_id
}

resource "azurerm_role_assignment" "webapp_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = local.webapp_principal_id
}

resource "azurerm_role_assignment" "webapp_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.webapp_principal_id
}

# ---------------------------------------------------------------- SigNoz VM managed identity (collector)

resource "azurerm_role_assignment" "signoz_vm_blob" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = local.signoz_vm_principal_id
}

resource "azurerm_role_assignment" "signoz_vm_eventhub" {
  scope                = azurerm_eventhub_namespace.main.id
  role_definition_name = "Azure Event Hubs Data Receiver"
  principal_id         = local.signoz_vm_principal_id
}

resource "azurerm_role_assignment" "signoz_vm_monitoring" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Monitoring Reader"
  principal_id         = local.signoz_vm_principal_id
}
