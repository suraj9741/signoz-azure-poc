# Windows support VM in its own VNet (optionally another region), peered to the main VNet.
# Used only for access: browser to the private Web App and SigNoz UI, SSMS to SQL.
# Reached through Bastion in the main VNet.

resource "azurerm_virtual_network" "support" {
  count               = var.enable_support_vm ? 1 : 0
  name                = local.names.support_vnet
  location            = var.support_location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = [var.support_vnet_address_space]
  tags                = local.tags
}

resource "azurerm_subnet" "support" {
  count                = var.enable_support_vm ? 1 : 0
  name                 = "snet-support"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.support[0].name
  address_prefixes     = [var.support_subnet_prefix]
}

resource "azurerm_virtual_network_peering" "main_to_support" {
  count                     = var.enable_support_vm ? 1 : 0
  name                      = "peer-${local.name_base}-to-${local.support_name_base}"
  resource_group_name       = azurerm_resource_group.main.name
  virtual_network_name      = azurerm_virtual_network.main.name
  remote_virtual_network_id = azurerm_virtual_network.support[0].id
  allow_forwarded_traffic   = true
}

resource "azurerm_virtual_network_peering" "support_to_main" {
  count                     = var.enable_support_vm ? 1 : 0
  name                      = "peer-${local.support_name_base}-to-${local.name_base}"
  resource_group_name       = azurerm_resource_group.main.name
  virtual_network_name      = azurerm_virtual_network.support[0].name
  remote_virtual_network_id = azurerm_virtual_network.main.id
  allow_forwarded_traffic   = true
}

resource "azurerm_network_security_group" "support" {
  count               = var.enable_support_vm ? 1 : 0
  name                = local.names.support_nsg
  location            = var.support_location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "allow-rdp-from-bastion"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = var.subnet_prefixes.bastion
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "support" {
  count                     = var.enable_support_vm ? 1 : 0
  subnet_id                 = azurerm_subnet.support[0].id
  network_security_group_id = azurerm_network_security_group.support[0].id
}

resource "azurerm_network_interface" "support_vm" {
  count               = var.enable_support_vm ? 1 : 0
  name                = local.names.support_nic
  location            = var.support_location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  ip_configuration {
    name                          = "ipconfig"
    subnet_id                     = azurerm_subnet.support[0].id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.support_vm_private_ip
  }
}

resource "azurerm_windows_virtual_machine" "support" {
  count                 = var.enable_support_vm ? 1 : 0
  name                  = local.names.support_vm
  computer_name         = "vm-support" # Windows host name, max 15 chars
  location              = var.support_location
  resource_group_name   = azurerm_resource_group.main.name
  size                  = var.support_vm_size
  admin_username        = var.support_vm_admin_username
  admin_password        = random_password.support_vm.result
  network_interface_ids = [azurerm_network_interface.support_vm[0].id]
  tags                  = local.tags

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
  }

  source_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2022-datacenter-azure-edition"
    version   = "latest"
  }
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "support" {
  count                 = var.enable_support_vm ? 1 : 0
  virtual_machine_id    = azurerm_windows_virtual_machine.support[0].id
  location              = var.support_location
  enabled               = true
  daily_recurrence_time = var.auto_shutdown_time
  timezone              = var.auto_shutdown_timezone
  tags                  = local.tags

  notification_settings {
    enabled = false
  }
}
