# SigNoz VM: runs SigNoz (Phase 3) and the OTel Collector (Phase 2). Private IP only.

resource "tls_private_key" "signoz_vm" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Private key saved locally for Bastion SSH; .ssh/ is git-ignored.
resource "local_sensitive_file" "signoz_vm_key" {
  content         = tls_private_key.signoz_vm.private_key_openssh
  filename        = "${path.module}/.ssh/${local.names.signoz_vm}.pem"
  file_permission = "0600"
}

resource "azurerm_network_interface" "signoz_vm" {
  name                = local.names.signoz_nic
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  ip_configuration {
    name                          = "ipconfig"
    subnet_id                     = azurerm_subnet.signoz.id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.signoz_vm_private_ip
  }
}

resource "azurerm_linux_virtual_machine" "signoz" {
  name                  = local.names.signoz_vm
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  size                  = var.signoz_vm_size
  admin_username        = "azureuser"
  network_interface_ids = [azurerm_network_interface.signoz_vm.id]
  custom_data           = base64encode(file("${path.module}/scripts/cloud-init-signoz.yaml"))
  tags                  = local.tags

  admin_ssh_key {
    username   = "azureuser"
    public_key = tls_private_key.signoz_vm.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.signoz_vm_disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  lifecycle {
    # cloud-init runs only at first boot; editing it must not recreate the VM.
    ignore_changes = [custom_data]
  }
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "signoz" {
  virtual_machine_id    = azurerm_linux_virtual_machine.signoz.id
  location              = azurerm_resource_group.main.location
  enabled               = true
  daily_recurrence_time = var.auto_shutdown_time
  timezone              = var.auto_shutdown_timezone
  tags                  = local.tags

  notification_settings {
    enabled = false
  }
}
