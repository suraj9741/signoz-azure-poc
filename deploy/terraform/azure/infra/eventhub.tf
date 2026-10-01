# Platform logs (diagnostic settings) land here; the collector reads them in Phase 3.
resource "azurerm_eventhub_namespace" "main" {
  name                          = local.names.eventhub_ns
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  sku                           = var.eventhub_sku
  capacity                      = 1
  public_network_access_enabled = false
  tags                          = local.tags

  # Diagnostic settings deliver through the "trusted Microsoft services" bypass;
  # without it a private-only namespace silently receives nothing.
  network_rulesets {
    default_action                 = "Deny"
    public_network_access_enabled  = false
    trusted_service_access_enabled = true
  }
}

resource "azurerm_eventhub" "platform_logs" {
  name              = local.names.eventhub
  namespace_id      = azurerm_eventhub_namespace.main.id
  partition_count   = var.eventhub_partition_count
  message_retention = var.eventhub_retention_days
}

resource "azurerm_eventhub_consumer_group" "otelcol" {
  name                = local.names.eventhub_consumer
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.platform_logs.name
  resource_group_name = azurerm_resource_group.main.name
}

# Diagnostic settings send through the namespace's root rule (Azure platform requirement).
data "azurerm_eventhub_namespace_authorization_rule" "root" {
  name                = "RootManageSharedAccessKey"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_private_endpoint" "eventhub" {
  name                = "pe-eventhub-${local.name_base}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-eventhub"
    private_connection_resource_id = azurerm_eventhub_namespace.main.id
    subresource_names              = ["namespace"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["eventhub"].id]
  }
}
