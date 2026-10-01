#!/usr/bin/env bash
# Run ON the SigNoz VM (as azureuser) from the copied collector/ folder:
#   ./install.sh <storage-account-name> [app-logs-container]
# Mounts the Blob log container read-only with blobfuse2 (VM managed identity)
# and starts the OpenTelemetry Collector with Docker Compose.
set -euo pipefail

STORAGE_ACCOUNT="${1:?usage: ./install.sh <storage-account-name> [container]}"
CONTAINER="${2:-app-logs}"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> blobfuse2 config"
sudo mkdir -p /etc/blobfuse2 /mnt/app-logs /mnt/blobfuse-cache
sudo tee /etc/blobfuse2/app-logs.yaml >/dev/null <<EOF
allow-other: true
read-only: true
logging:
  type: syslog
  level: log_warning
components:
  - libfuse
  - file_cache
  - attr_cache
  - azstorage
libfuse:
  attribute-expiration-sec: 30
  entry-expiration-sec: 30
  negative-entry-expiration-sec: 30
file_cache:
  path: /mnt/blobfuse-cache
  timeout-sec: 30
attr_cache:
  timeout-sec: 30
azstorage:
  type: block
  account-name: ${STORAGE_ACCOUNT}
  container: ${CONTAINER}
  endpoint: https://${STORAGE_ACCOUNT}.blob.core.windows.net
  mode: msi
EOF
grep -q '^user_allow_other' /etc/fuse.conf || echo 'user_allow_other' | sudo tee -a /etc/fuse.conf >/dev/null

echo "==> blobfuse2 mount as a systemd service (survives reboots)"
sudo tee /etc/systemd/system/blobfuse2-app-logs.service >/dev/null <<'EOF'
[Unit]
Description=blobfuse2 mount of app-logs (read-only)
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=/usr/bin/blobfuse2 mount /mnt/app-logs --config-file=/etc/blobfuse2/app-logs.yaml
ExecStop=/usr/bin/fusermount3 -u /mnt/app-logs
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now blobfuse2-app-logs.service
sleep 5
if mountpoint -q /mnt/app-logs; then
  echo "    mounted: $(ls /mnt/app-logs | head -5 | tr '\n' ' ')"
else
  echo "    WARNING: /mnt/app-logs not mounted — check: journalctl -u blobfuse2-app-logs"
fi

echo "==> start collector"
cd "$HERE"
sudo docker compose up -d
sleep 5
curl -fsS http://localhost:13133/ && echo "    collector healthy"
echo
echo "Watch incoming telemetry:  sudo docker logs -f otelcol"
