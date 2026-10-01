output "resource_group" {
  value = azurerm_resource_group.main.name
}

# ---------------------------------------------------------------- access

output "bastion_name" {
  value = var.enable_bastion ? azurerm_bastion_host.main[0].name : null
}

output "support_vm_name" {
  value = var.enable_support_vm ? azurerm_windows_virtual_machine.support[0].name : null
}

output "support_vm_login" {
  value = var.enable_support_vm ? "Portal → ${azurerm_windows_virtual_machine.support[0].name} → Connect → Bastion. User ${var.support_vm_admin_username}; password: az keyvault secret show --vault-name ${azurerm_key_vault.main.name} -n support-vm-admin-password --query value -o tsv" : null
}

output "signoz_vm_name" {
  value = azurerm_linux_virtual_machine.signoz.name
}

output "signoz_vm_private_ip" {
  value = azurerm_network_interface.signoz_vm.private_ip_address
}

output "signoz_vm_ssh_command" {
  value = var.enable_bastion ? "az network bastion ssh -g ${azurerm_resource_group.main.name} -n ${azurerm_bastion_host.main[0].name} --target-resource-id ${azurerm_linux_virtual_machine.signoz.id} --auth-type ssh-key --username azureuser --ssh-key ${local_sensitive_file.signoz_vm_key.filename}" : null
}

output "signoz_ui_url" {
  value = "http://${azurerm_network_interface.signoz_vm.private_ip_address}:8080 (from the support VM, Phase 3)"
}

# ---------------------------------------------------------------- app and data

output "webapp_name" {
  value = azurerm_linux_web_app.api.name
}

output "webapp_url" {
  value = "https://${azurerm_linux_web_app.api.default_hostname} (private — from the support VM)"
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "sql_server_fqdn" {
  value = azurerm_mssql_server.main.fully_qualified_domain_name
}

output "sql_database" {
  value = azurerm_mssql_database.main.name
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "storage_account" {
  value = azurerm_storage_account.main.name
}

output "eventhub_namespace" {
  value = azurerm_eventhub_namespace.main.name
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}
