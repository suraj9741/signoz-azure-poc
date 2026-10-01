# Basic SKU has no private endpoint; access is by managed identity only (admin user off).
resource "azurerm_container_registry" "main" {
  name                = local.names.acr
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.acr_sku
  admin_enabled       = false
  tags                = local.tags
}
