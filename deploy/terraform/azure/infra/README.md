# SigNoz POC — Azure infrastructure

One file per component; per-deployment settings in `environments/*.tfvars`.

| Component | File |
| --- | --- |
| Resource group, naming, tags | `main.tf` |
| VNet, subnets, SigNoz NSG | `network.tf` |
| Private DNS zones + links | `dns.tf` |
| Bastion | `bastion.tf` |
| SigNoz VM (Linux) | `signoz_vm.tf` |
| Support VM (Windows), its VNet, peering | `support_vm.tf` |
| App Service plan + Web App | `webapp.tf` |
| Container registry | `acr.tf` |
| Azure SQL | `sql_server.tf` |
| Storage (app text logs) | `storageaccount.tf` |
| Key Vault | `keyvault.tf` |
| Generated passwords → Key Vault | `secret.tf` |
| Event Hub | `eventhub.tf` |
| Diagnostic settings → Event Hub | `diagnostics.tf` |
| Role assignments | `rbac.tf` |
| SigNoz VM bootstrap | `scripts/cloud-init-signoz.yaml` |
| Per-deployment settings | `environments/*.tfvars` |

## Deploy

One Terraform workspace (separate state) per deployment, named like its tfvars file.

```bash
az login
az account set --subscription <subscription-id>
terraform init
terraform workspace new poc-uksouth      # first time; later: terraform workspace select poc-uksouth
terraform plan  -var-file=environments/poc-uksouth.tfvars -out=poc-uksouth.tfplan
terraform apply poc-uksouth.tfplan
```

## New region or account

1. Copy `environments/example.tfvars` to `environments/<name>.tfvars` and set subscription, regions, address ranges.
2. `terraform workspace new <name>`
3. Plan/apply with `-var-file=environments/<name>.tfvars`.

No code changes needed. Names include the region code, and globally unique names get a random suffix, so deployments never clash.

## Cost switches

- `enable_bastion = false` → apply: removes Bastion (largest cost) when idle.
- VMs auto-shut down daily at `auto_shutdown_time`.

## Destroy

```bash
terraform destroy -var-file=environments/poc-uksouth.tfvars
```

State (`terraform.tfstate.d/`) and `.ssh/` hold secrets and are git-ignored.
