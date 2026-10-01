resource "azurerm_service_plan" "main" {
  name                = local.names.app_service_plan
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = local.tags
}

locals {
  # Phase 1 runs a public placeholder; Phase 2 sets var.app_image to our image in ACR.
  use_app_image = var.app_image != null

  webapp_registry_url = local.use_app_image ? "https://${azurerm_container_registry.main.login_server}" : var.webapp_placeholder_image.registry_url
  webapp_image        = local.use_app_image ? var.app_image : var.webapp_placeholder_image.image
  webapp_port         = local.use_app_image ? var.app_port : var.webapp_placeholder_image.port

  # OpenTelemetry auto-instrumentation is configured only through settings (no code change).
  otel_app_settings = {
    OTEL_SERVICE_NAME                                   = var.otel_service_name
    OTEL_RESOURCE_ATTRIBUTES                            = "deployment.environment=${var.environment},tenant.id=${var.otel_tenant},cloud.region=${var.location}"
    OTEL_EXPORTER_OTLP_ENDPOINT                         = "http://${var.signoz_vm_private_ip}:4318"
    OTEL_EXPORTER_OTLP_PROTOCOL                         = "http/protobuf"
    OTEL_TRACES_EXPORTER                                = "otlp"
    OTEL_METRICS_EXPORTER                               = "otlp"
    OTEL_LOGS_EXPORTER                                  = "otlp"
    OTEL_DOTNET_AUTO_TRACES_ADDITIONAL_SOURCES          = "DqLite.Api"
    OTEL_DOTNET_AUTO_METRICS_ADDITIONAL_SOURCES         = "DqLite.Api"
    OTEL_DOTNET_AUTO_SQLCLIENT_SET_DBSTATEMENT_FOR_TEXT = "true"
  }
}

resource "azurerm_linux_web_app" "api" {
  name                          = local.names.webapp
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  service_plan_id               = azurerm_service_plan.main.id
  https_only                    = true
  public_network_access_enabled = false
  virtual_network_subnet_id     = azurerm_subnet.app_integration.id
  tags                          = local.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    vnet_route_all_enabled                  = true
    container_registry_use_managed_identity = local.use_app_image
    health_check_path                       = local.use_app_image ? "/healthz" : "/"
    health_check_eviction_time_in_min       = 10

    application_stack {
      docker_registry_url = local.webapp_registry_url
      docker_image_name   = local.webapp_image
    }
  }

  app_settings = merge({
    WEBSITES_PORT              = local.webapp_port
    ConnectionStrings__Default = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=${azurerm_key_vault_secret.sql_connection_string.name})"
    APP_LOGS_STORAGE_ACCOUNT   = azurerm_storage_account.main.name
    APP_LOGS_CONTAINER         = azurerm_storage_container.app_logs.name
    TEST_ENDPOINTS_ENABLED     = tostring(var.app_test_endpoints_enabled)
  }, local.use_app_image ? local.otel_app_settings : {})
}

resource "azurerm_private_endpoint" "webapp" {
  name                = "pe-webapp-${local.name_base}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-webapp"
    private_connection_resource_id = azurerm_linux_web_app.api.id
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["webapp"].id]
  }
}
