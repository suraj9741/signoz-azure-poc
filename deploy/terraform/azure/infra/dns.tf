locals {
  private_dns_zones = {
    webapp   = "privatelink.azurewebsites.net"
    sql      = "privatelink.database.windows.net"
    blob     = "privatelink.blob.core.windows.net"
    eventhub = "privatelink.servicebus.windows.net"
    keyvault = "privatelink.vaultcore.azure.net"
  }
}

resource "azurerm_private_dns_zone" "zones" {
  for_each            = local.private_dns_zones
  name                = each.value
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "main" {
  for_each              = local.private_dns_zones
  name                  = "link-${each.key}-${local.name_base}"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.zones[each.key].name
  virtual_network_id    = azurerm_virtual_network.main.id
  tags                  = local.tags
}

# Support VM resolves private endpoints too.
resource "azurerm_private_dns_zone_virtual_network_link" "support" {
  for_each              = var.enable_support_vm ? local.private_dns_zones : {}
  name                  = "link-${each.key}-${local.support_name_base}"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.zones[each.key].name
  virtual_network_id    = azurerm_virtual_network.support[0].id
  tags                  = local.tags
}
