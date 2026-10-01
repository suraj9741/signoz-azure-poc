# All secrets are generated here and stored in this deployment's Key Vault.
# Nothing secret goes in .tfvars or git.

resource "random_password" "sql_admin" {
  length           = 24
  special          = true
  override_special = "!#%*-_"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

resource "random_password" "support_vm" {
  length           = 20
  special          = true
  override_special = "!#%*-_"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

resource "azurerm_key_vault_secret" "sql_admin_password" {
  name         = "sql-admin-password"
  value        = random_password.sql_admin.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.runner_key_vault]
}

resource "azurerm_key_vault_secret" "sql_connection_string" {
  name         = "sql-connection-string"
  value        = "Server=tcp:${azurerm_mssql_server.main.fully_qualified_domain_name},1433;Database=${azurerm_mssql_database.main.name};User ID=${var.sql_admin_login};Password=${random_password.sql_admin.result};Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.runner_key_vault]
}

resource "azurerm_key_vault_secret" "support_vm_password" {
  count        = var.enable_support_vm ? 1 : 0
  name         = "support-vm-admin-password"
  value        = random_password.support_vm.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.runner_key_vault]
}

resource "azurerm_key_vault_secret" "signoz_vm_ssh_key" {
  name         = "signoz-vm-ssh-private-key"
  value        = tls_private_key.signoz_vm.private_key_openssh
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.runner_key_vault]
}
