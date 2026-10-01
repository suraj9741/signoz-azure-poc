# Platform logs → Event Hub. Platform metrics stay in Azure Monitor automatically
# and are pulled by the collector (azuremonitor receiver) in Phase 3.

resource "azurerm_monitor_diagnostic_setting" "webapp" {
  name                           = "diag-to-eventhub"
  target_resource_id             = azurerm_linux_web_app.api.id
  eventhub_name                  = azurerm_eventhub.platform_logs.name
  eventhub_authorization_rule_id = data.azurerm_eventhub_namespace_authorization_rule.root.id

  enabled_log {
    category_group = "allLogs"
  }
}

resource "azurerm_monitor_diagnostic_setting" "sql_database" {
  name                           = "diag-to-eventhub"
  target_resource_id             = azurerm_mssql_database.main.id
  eventhub_name                  = azurerm_eventhub.platform_logs.name
  eventhub_authorization_rule_id = data.azurerm_eventhub_namespace_authorization_rule.root.id

  enabled_log {
    category_group = "allLogs"
  }
}
