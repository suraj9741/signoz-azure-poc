resource "azurerm_mssql_server" "main" {
  name                          = local.names.sql_server
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  version                       = "12.0"
  administrator_login           = var.sql_admin_login
  administrator_login_password  = random_password.sql_admin.result
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false
  tags                          = local.tags
}

resource "azurerm_mssql_database" "main" {
  name                 = var.sql_database_name
  server_id            = azurerm_mssql_server.main.id
  sku_name             = var.sql_sku
  max_size_gb          = var.sql_max_size_gb
  storage_account_type = "Local"
  tags                 = local.tags
}

resource "azurerm_private_endpoint" "sql" {
  name                = "pe-sql-${local.name_base}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-sql"
    private_connection_resource_id = azurerm_mssql_server.main.id
    subresource_names              = ["sqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["sql"].id]
  }
}
