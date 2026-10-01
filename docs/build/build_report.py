"""Builds docs/signoz-poc-report.html and docs/architecture.html from report.template.html.

Usage: python3 docs/build/build_report.py   (logos are read from docs/build/icons)

Embeds technology/service logos as data URIs (Azure icons from the draw.io azure2 library; OpenTelemetry/.NET/Docker/ClickHouse/Terraform/PostgreSQL/Ubuntu from simple-icons;
SigNoz brand mark), and generates the interactive architecture views and the issue list.
"""
import base64
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
ICONS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "icons"
OUT = HERE.parent / "signoz-poc-report.html"

BRAND_COLORS = {  # simple-icons are monochrome paths; tint with brand colour
    "opentelemetry": "#F5A800", "dotnet": "#512BD4", "docker": "#2496ED", "clickhouse": "#FFCC01",
    "terraform": "#844FBA", "postgresql": "#4169E1", "ubuntu": "#E95420",
}


def data_uri(name: str) -> str:
    p = ICONS / f"{name}.svg"
    svg = p.read_text()
    if name in BRAND_COLORS and "fill=" not in svg.split(">", 1)[0]:
        svg = svg.replace("<svg ", f'<svg fill="{BRAND_COLORS[name]}" ', 1)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


PERSON = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="7.5" r="4" fill="#5c6b7d"/>'
    b'<path d="M3.5 21c.8-4.6 4.2-7.2 8.5-7.2s7.7 2.6 8.5 7.2z" fill="#5c6b7d"/></svg>').decode())
BELL = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0-6 6v4l-2 3h16l-2-3V9a6 6 0 0 0-6-6z" fill="#d9480f"/>'
    b'<circle cx="12" cy="19.5" r="2" fill="#d9480f"/></svg>').decode())
DASH = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="18" rx="2" fill="#0f6cbd"/>'
    b'<rect x="4.5" y="12" width="3" height="6" fill="#fff"/><rect x="10.5" y="8" width="3" height="10" fill="#fff"/>'
    b'<rect x="16.5" y="5.5" width="3" height="12.5" fill="#fff"/></svg>').decode())
MAIL = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2" fill="#5c6b7d"/>'
    b'<path d="M3 6.5l9 6.5 9-6.5" stroke="#fff" stroke-width="1.6" fill="none"/></svg>').decode())

I = {k: data_uri(v) for k, v in {
    "vnet": "az_Virtual_Networks", "subnet": "az_Subnet", "nsg": "az_Network_Security_Groups",
    "bastion": "az_Bastions", "pe": "az_Private_Link", "dns": "az_DNS_Zones", "pip": "az_Public_IP_Addresses",
    "peering": "az_Connections", "vm": "az_Virtual_Machine", "app": "az_App_Services",
    "plan": "az_App_Service_Plans", "sql": "az_SQL_Database", "storage": "az_Storage_Accounts",
    "kv": "az_Key_Vaults", "acr": "az_Container_Registries", "eh": "az_Event_Hubs", "monitor": "az_Monitor",
    "mi": "az_Managed_Identities", "rg": "az_Resource_Groups", "otel": "opentelemetry", "dotnet": "dotnet",
    "docker": "docker", "clickhouse": "clickhouse", "terraform": "terraform", "postgres": "postgresql",
    "ubuntu": "ubuntu", "signoz": "signoz"}.items()}
I.update({"user": PERSON, "bell": BELL, "dash": DASH, "mail": MAIL})

# ------------------------------------------------------------------ diagram model
# node: id -> (x, y, icon, label, sublabel, title, detail)
NODE_W, NODE_H = 118, 84


def node(nid, x, y, icon, label, sub, title, detail, w=NODE_W):
    return {"id": nid, "x": x, "y": y, "icon": icon, "label": label, "sub": sub, "title": title,
            "detail": detail, "w": w}


def render_view(vid, width, height, zones, nodes, edges):
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(vid)} architecture view" '
           f'xmlns="http://www.w3.org/2000/svg">',
           '<defs>' + ''.join(
               f'<marker id="a-{vid}-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
               f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" style="fill:var(--edge-{c})"/></marker>'
               for c in ("req", "otlp", "log", "met", "data")) + '</defs>']
    for z in zones:
        x, y, w, h, t, cls = z
        out.append(f'<rect class="zone {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
        out.append(f'<text class="zone-t" x="{x + 12}" y="{y + 20}">{html.escape(t)}</text>')
    for e in edges:
        pts, cls, lab = e[0], e[1], e[2] if len(e) > 2 else ""
        d = "M" + " L".join(f"{px} {py}" for px, py in pts)
        out.append(f'<path class="e {cls}" d="{d}" marker-end="url(#a-{vid}-{cls})"/>')
        if lab:
            (x1, y1), (x2, y2) = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 5
            out.append(f'<text class="el" x="{lx}" y="{ly}" text-anchor="middle">{html.escape(lab)}</text>')
    for n in nodes:
        x, y, w = n["x"], n["y"], n["w"]
        out.append(f'<g class="node" tabindex="0" role="button" data-id="{vid}:{n["id"]}" '
                   f'aria-label="{html.escape(n["title"])}">')
        out.append(f'<rect class="card hit" x="{x}" y="{y}" width="{w}" height="{NODE_H}" rx="8"/>')
        out.append(f'<image href="{I[n["icon"]]}" x="{x + w / 2 - 17}" y="{y + 8}" width="34" height="34"/>')
        out.append(f'<text class="lbl" x="{x + w / 2}" y="{y + 58}" text-anchor="middle">{html.escape(n["label"])}</text>')
        if n["sub"]:
            out.append(f'<text class="sub" x="{x + w / 2}" y="{y + 73}" text-anchor="middle">{html.escape(n["sub"])}</text>')
        out.append('</g>')
    out.append('</svg>')
    return "".join(out)


INFO = {}


def add(vid, nodes):
    for n in nodes:
        INFO[f"{vid}:{n['id']}"] = {"t": n["title"], "d": n["detail"]}


# ---- View 1: overview
ov_nodes = [
    node("user", 30, 70, "user", "Engineer", "Azure portal", "Engineer",
         "Signs in to the Azure portal and connects to the support VM through Bastion. No workload has a public IP."),
    node("bastion", 250, 70, "bastion", "Bastion", "Standard · public IP", "Azure Bastion bas-sigpoc-poc-cin",
         "Standard SKU with tunnelling, in AzureBastionSubnet 10.20.0.0/26. RDP to the support VM over global peering; SSH to the SigNoz VM. Toggle with enable_bastion."),
    node("support", 30, 330, "vm", "Support VM", "Windows · B2s_v2", "vm-support-sigpoc-poc-sin (South India)",
         "Windows Server 2022, 10.30.1.10, no public IP. Edge opens the private Web App and the SigNoz UI (http://10.20.1.10:8080). Password in Key Vault."),
    node("app", 250, 300, "app", "Web App", "dqlite-api · B1", "app-dqlite-sigpoc-poc-cin-xxxxx",
         "Linux container dqlite-api:v1 from ACR (managed identity). Public access disabled; private endpoint 10.20.3.8; VNet integration through snet-app-integration with route-all. Health check /healthz."),
    node("agent", 390, 300, "dotnet", ".NET 8 + OTel", "auto-instrumentation", "OpenTelemetry .NET auto-instrumentation v1.17.0",
         "Profiler and startup hook baked into the image. Configured only by app settings: OTLP/HTTP to 10.20.1.10:4318, service.name=dqlite-api, deployment.environment=poc, tenant.id=demo."),
    node("sql", 250, 540, "sql", "Azure SQL", "sqldb-dqlite · Basic", "sql-sigpoc-poc-cin-xxxxx / sqldb-dqlite",
         "Private endpoint 10.20.3.5, public access off, TLS 1.2. 20,000 seeded rows. Diagnostic logs (allLogs) to Event Hub."),
    node("kv", 380, 540, "kv", "Key Vault", "RBAC · PE", "kv-sigpoc-poc-xxxxx",
         "SQL password and connection string, support VM password, SigNoz VM SSH key. The Web App reads the connection string through a Key Vault reference over the private endpoint 10.20.3.7."),
    node("blob", 510, 540, "storage", "Blob storage", "app-logs", "stsigpocpocxxxxx / app-logs",
         "Plain-text logs written by the app every 30 s with managed identity. Private endpoint 10.20.3.6; shared keys disabled. Mounted read-only on the SigNoz VM by blobfuse2."),
    node("eh", 640, 540, "eh", "Event Hub", "platform-logs", "evhns-sigpoc-poc-cin-xxxxx / platform-logs",
         "Standard, 1 TU, private endpoint 10.20.3.4, trusted Microsoft services enabled so diagnostic settings can deliver. Consumer group otelcol."),
    node("otelcol", 620, 190, "otel", "OTel Collector", "contrib 0.161.0", "otelcol (Docker, SigNoz VM)",
         "Receivers: otlp (4317/4318), filelog/blob, azure_event_hub, azure_monitor, hostmetrics. Processors: memory_limiter, resource/env, resourcedetection, batch. Exporter: otlp to ingester:4317 with a disk-backed queue."),
    node("ingester", 770, 190, "signoz", "SigNoz ingester", "v0.144.11", "signoz-ingester-1",
         "SigNoz's collector. No host ports; reached by our collector over the signoz-network Docker network. Opens only after the first admin sign-up (OpAMP configuration)."),
    node("ch", 920, 190, "clickhouse", "ClickHouse", "25.12.5 · 8 GB cap", "signoz-telemetrystore-clickhouse-0-0",
         "Stores traces, logs and metrics. Coordinated by ClickHouse Keeper. Data on the VM OS disk (64 GB)."),
    node("keeper", 1060, 190, "clickhouse", "Keeper", "coordination", "signoz-telemetrykeeper-clickhousekeeper-0",
         "ClickHouse Keeper, replacing ZooKeeper in the Foundry deployment."),
    node("ui", 770, 320, "signoz", "SigNoz UI", "v0.143.0 · :8080", "signoz-signoz-0",
         "Query service, UI, alert evaluation and OpAMP server. UI on 8080, reachable only from the support VM subnet."),
    node("pg", 920, 320, "postgres", "Postgres", "metastore", "signoz-metastore-postgres-0",
         "Holds users, organisation, dashboards and alert rules."),
    node("dash", 1060, 320, "dash", "Dashboards", "Stage D", "Dashboards (planned)",
         "Planned DQ Lite dashboard: request rate, error rate, p95, SQL latency, rule runs, Azure SQL DTU, Web App Http5xx, error logs. Not built yet."),
    node("alert", 1060, 430, "bell", "Alerts", "Stage D", "Alert rules (planned)",
         "Planned: error rate > 5%, p95 > 1 s, database errors, service down. Email channel. Not configured yet."),
    node("acr", 820, 560, "acr", "Container Registry", "Basic", "crsigpocpocxxxxx",
         "Holds dqlite-api:v1. Admin user off; the Web App pulls with AcrPull. Basic has no private endpoint."),
    node("monitor", 960, 560, "monitor", "Azure Monitor", "metrics API", "Azure Monitor metrics API",
         "Platform metrics for the Web App, App Service plan and SQL database, pulled every 60 s by azure_monitor using the VM identity (Monitoring Reader)."),
    node("mi", 1090, 560, "mi", "Managed identities", "Web App · VM", "System-assigned managed identities",
         "Web App: AcrPull, Key Vault Secrets User, Blob Data Contributor. SigNoz VM: Blob Data Reader, Event Hubs Data Receiver, Monitoring Reader."),
]
ov_zones = [
    (10, 290, 180, 150, "South India · vnet-sigpoc-poc-sin", "az"),
    (215, 20, 975, 650, "Central India · vnet-sigpoc-poc-cin · rg-sigpoc-poc-cin", "az"),
    (235, 50, 150, 120, "AzureBastionSubnet", "sn"),
    (235, 270, 290, 140, "snet-app-integration", "sn"),
    (235, 505, 540, 140, "snet-private-endpoints", "sn"),
    (600, 150, 580, 330, "snet-signoz · vm-signoz-sigpoc-poc-cin (B4as_v2, 10.20.1.10)", "sn"),
    (800, 505, 380, 140, "Azure platform services", ""),
]
ov_edges = [
    ([(148, 112), (250, 112)], "req", "HTTPS"),
    ([(309, 154), (309, 250), (148, 330)], "req", "RDP"),
    ([(148, 372), (250, 342)], "req", "HTTPS via PE"),
    ([(309, 384), (309, 540)], "data", "TDS 1433"),
    ([(360, 384), (439, 540)], "data", ""),
    ([(420, 384), (569, 540)], "log", "text logs"),
    ([(508, 330), (620, 250)], "otlp", "OTLP 4318"),
    ([(569, 540), (660, 274)], "log", "blobfuse2"),
    ([(699, 540), (699, 274)], "log", "Event Hub"),
    ([(309, 624), (309, 660), (720, 660), (720, 624)], "log", "diagnostic logs"),
    ([(738, 232), (770, 232)], "otlp", ""),
    ([(888, 232), (920, 232)], "otlp", ""),
    ([(1019, 274), (829, 320)], "data", ""),
    ([(1019, 232), (1060, 232)], "data", ""),
    ([(888, 362), (920, 362)], "data", ""),
    ([(888, 362), (1060, 362)], "data", ""),
    ([(888, 390), (1060, 460)], "data", ""),
    ([(1019, 560), (700, 274)], "met", "metrics API"),
    ([(879, 560), (309, 384)], "data", "image pull"),
    ([(148, 390), (770, 380)], "req", "UI :8080"),
]
add("ov", ov_nodes)
VIEW_OV = render_view("ov", 1200, 690, ov_zones, ov_nodes, ov_edges)

# ---- View 2: network
nw_nodes = [
    node("pip", 30, 60, "pip", "Public IP", "pip-bas-…", "pip-bas-sigpoc-poc-cin",
         "Standard static public IP used only by Bastion. The only public address in the deployment."),
    node("bas", 230, 60, "bastion", "Bastion", "10.20.0.0/26", "AzureBastionSubnet",
         "Bastion Standard with tunnelling. Source of the SSH (22) and RDP (3389) NSG allow rules."),
    node("nsg1", 430, 60, "nsg", "nsg-signoz", "4 inbound rules", "nsg-signoz-sigpoc-poc-cin",
         "100 SSH from 10.20.0.0/26 · 110 SSH+8080 from 10.30.1.0/24 · 120 OTLP 4317/4318 from 10.20.2.0/26 · 4000 deny VirtualNetwork."),
    node("vmsn", 630, 60, "vm", "snet-signoz", "10.20.1.0/24", "snet-signoz",
         "SigNoz VM at 10.20.1.10. The only subnet with an NSG in the main VNet."),
    node("appsn", 230, 220, "subnet", "snet-app-integration", "10.20.2.0/26", "snet-app-integration",
         "Delegated to Microsoft.Web/serverFarms. App Service outbound traffic with vnet_route_all_enabled, so all app egress uses private DNS and private endpoints.", w=150),
    node("pesn", 430, 220, "pe", "snet-private-endpoints", "10.20.3.0/27", "snet-private-endpoints",
         "Private endpoints: Event Hub 10.20.3.4, SQL .5, Blob .6, Key Vault .7, Web App .8 (observed with dig).", w=150),
    node("dns", 630, 220, "dns", "Private DNS", "5 zones · 10 links", "Private DNS zones",
         "privatelink.azurewebsites.net, database.windows.net, blob.core.windows.net, servicebus.windows.net, vaultcore.azure.net. Linked to both VNets so the support VM resolves private IPs."),
    node("peer", 830, 140, "peering", "Global peering", "cin ⇄ sin", "VNet peering (two links)",
         "peer-sigpoc-poc-cin-to-sigpoc-poc-sin and reverse, forwarded traffic allowed. Lets Bastion reach the support VM and the support VM reach the Web App, SQL and SigNoz UI."),
    node("supsn", 1020, 60, "subnet", "snet-support", "10.30.1.0/24", "snet-support (South India)",
         "Support VM at 10.30.1.10."),
    node("nsg2", 1020, 220, "nsg", "nsg-support", "RDP from Bastion", "nsg-support-sigpoc-poc-sin",
         "100 RDP 3389 from 10.20.0.0/26 · 4000 deny VirtualNetwork."),
]
nw_zones = [
    (10, 20, 790, 310, "vnet-sigpoc-poc-cin · 10.20.0.0/16 · Central India", "az"),
    (1000, 20, 180, 310, "vnet-sigpoc-poc-sin · 10.30.0.0/16", "az"),
]
nw_edges = [
    ([(148, 102), (230, 102)], "req", ""),
    ([(348, 102), (430, 102)], "req", "SSH"),
    ([(548, 102), (630, 102)], "req", ""),
    ([(380, 262), (430, 262)], "data", "private"),
    ([(580, 262), (630, 262)], "data", "resolves"),
    ([(748, 182), (830, 182)], "req", ""),
    ([(948, 182), (1020, 102)], "req", "RDP"),
]
add("nw", nw_nodes)
VIEW_NW = render_view("nw", 1200, 350, nw_zones, nw_nodes, nw_edges)

# ---- View 3: telemetry pipeline
tp_nodes = [
    node("s_app", 20, 50, "dotnet", "dqlite-api", "OTLP/HTTP", "Application (auto-instrumented)",
         "Traces, metrics and logs from the OpenTelemetry .NET agent. Custom ActivitySource/Meter DqLite.Api."),
    node("s_blob", 20, 150, "storage", "Blob text logs", "blobfuse2 mount", "Blob app-logs",
         "Files app-logs/yyyy/MM/dd/app-HHmmss-<instance>.log mounted read-only at /mnt/app-logs."),
    node("s_eh", 20, 250, "eh", "Event Hub", "diagnostic logs", "Event Hub platform-logs",
         "AppServiceConsoleLogs, AppServiceHTTPLogs, SQL database categories (e.g. DatabaseWaitStatistics)."),
    node("s_mon", 20, 350, "monitor", "Azure Monitor", "metrics API", "Azure Monitor API",
         "Microsoft.Web/sites, Microsoft.Web/serverFarms, Microsoft.Sql/servers/databases in rg-sigpoc-poc-cin."),
    node("s_host", 20, 450, "ubuntu", "SigNoz VM host", "/hostfs", "Host (Ubuntu 24.04)",
         "CPU, load, memory, disk, filesystem, network, paging, processes."),
    node("r_otlp", 230, 50, "otel", "otlp", ":4317 / :4318", "Receiver otlp", "gRPC 4317, HTTP 4318."),
    node("r_file", 230, 150, "otel", "filelog/blob", "regex parser", "Receiver filelog/blob",
         "Parses time, level (INF/WRN/ERR/CRT/DBG → severity), category, message. Offsets kept in file_storage."),
    node("r_eh", 230, 250, "otel", "azure_event_hub", "managed identity", "Receiver azure_event_hub",
         "auth: azure_auth (VM identity), group otelcol, format azure. Needs collector-contrib ≥ 0.161."),
    node("r_mon", 230, 350, "otel", "azure_monitor", "every 60 s", "Receiver azure_monitor",
         "auth.authenticator: azure_auth. 156 metric names collected."),
    node("r_host", 230, 450, "otel", "hostmetrics", "every 30 s", "Receiver hostmetrics", "root_path /hostfs, pid: host."),
    node("p", 440, 240, "otel", "Processors", "limit · enrich · batch", "Processors",
         "memory_limiter → resource/env (deployment.environment, tenant.id) → resourcedetection/host (host pipeline only) → batch.", w=130),
    node("x", 630, 240, "otel", "otlp/signoz", "queue + retry", "Exporter otlp/signoz",
         "endpoint ingester:4317 on signoz-network, insecure gRPC, sending_queue on file_storage, retry up to 10 minutes."),
    node("ing", 820, 240, "signoz", "Ingester", "v0.144.11", "SigNoz ingester", "Writes to ClickHouse."),
    node("chx", 1000, 150, "clickhouse", "ClickHouse", "traces · logs · metrics", "ClickHouse",
         "signoz_traces, signoz_logs, signoz_metrics databases."),
    node("uix", 1000, 330, "signoz", "SigNoz", "UI · alerts", "SigNoz query service and UI",
         "Services, Traces, Logs, Metrics, Infrastructure, Dashboards, Alerts."),
]
tp_zones = [
    (10, 20, 140, 530, "Sources", ""),
    (215, 20, 150, 530, "Receivers", "sn"),
    (420, 20, 360, 530, "otelcol (contrib 0.161.0)", "az"),
    (800, 20, 380, 530, "SigNoz (Foundry, v0.143.0)", "az"),
]
tp_edges = [
    ([(138, 92), (230, 92)], "otlp"), ([(138, 192), (230, 192)], "log"), ([(138, 292), (230, 292)], "log"),
    ([(138, 392), (230, 392)], "met"), ([(138, 492), (230, 492)], "met"),
    ([(348, 92), (440, 260)], "otlp"), ([(348, 192), (440, 270)], "log"), ([(348, 292), (440, 282)], "log"),
    ([(348, 392), (440, 296)], "met"), ([(348, 492), (440, 310)], "met"),
    ([(570, 282), (630, 282)], "otlp"), ([(748, 282), (820, 282)], "otlp", "OTLP gRPC"),
    ([(938, 270), (1000, 192)], "data"), ([(1059, 234), (1059, 330)], "data", "query"),
]
add("tp", tp_nodes)
VIEW_TP = render_view("tp", 1200, 570, tp_zones, tp_nodes, tp_edges)


def legend_line(cls, text):
    return (f'<div class="row"><svg width="34" height="10" aria-hidden="true"><line x1="0" y1="5" x2="34" y2="5" '
            f'style="stroke:var(--edge-{cls});stroke-width:2.5{";stroke-dasharray:5 4" if cls == "data" else ""}"/></svg>{text}</div>')


DIAGRAM = f'''
<div class="diagram" id="arch">
  <div class="dtabs" role="tablist" aria-label="Architecture views">
    <button role="tab" aria-selected="true" data-view="ov">Overview</button>
    <button role="tab" aria-selected="false" data-view="nw">Network detail</button>
    <button role="tab" aria-selected="false" data-view="tp">Telemetry pipeline</button>
  </div>
  <div class="dcanvas" data-v="ov">{VIEW_OV}</div>
  <div class="dcanvas" data-v="nw" hidden>{VIEW_NW}</div>
  <div class="dcanvas" data-v="tp" hidden>{VIEW_TP}</div>
  <div class="dpanel">
    <div class="info" id="dinfo" aria-live="polite"><h4>Select a component</h4>
      <p>Click or tab to any icon to see its configuration and connections. The overview shows the full request and telemetry path; the other views zoom into networking and the collector pipeline.</p></div>
    <div class="legend">
      {legend_line("req", "User / request traffic")}
      {legend_line("otlp", "OTLP traces, metrics, logs")}
      {legend_line("log", "Logs (Blob, Event Hub)")}
      {legend_line("met", "Metrics (Azure Monitor, host)")}
      {legend_line("data", "Data / internal / image pull")}
      <div class="row"><svg width="34" height="14" aria-hidden="true"><rect x="1" y="1" width="32" height="12" rx="3" style="fill:none;stroke:var(--azure);stroke-dasharray:6 4"/></svg>VNet / region</div>
      <div class="row"><svg width="34" height="14" aria-hidden="true"><rect x="1" y="1" width="32" height="12" rx="3" style="fill:none;stroke:var(--edge-data);stroke-dasharray:3 3"/></svg>Subnet / group</div>
    </div>
  </div>
</div>'''

# ------------------------------------------------------------------ issues (all observed during the POC)
ISSUES = [
    dict(t="Plan document could not be opened", where="Claude desktop file link", err="Link to “SigNoz Azure POC - Implementation and Validation Plan.md” did not open",
         cause="Spaces in the file name broke the clickable link.", steps="Checked the file existed on disk; it did.",
         fix="Renamed to SigNoz-Azure-POC-Plan.md and sent the file directly.", change="File rename only.",
         valid="File rendered in the side panel.", lesson="Avoid spaces in names of files shared through links.", sev="Minor"),
    dict(t="First plan too broad for the need", where="Planning", err="Feedback: “this is to complex we want small POC”",
         cause="The first plan covered production-grade scope (Container Apps collector, 13 tests, 9 alerts).",
         steps="Reviewed with the team; agreed 3 phases, 1 environment.", fix="Rewrote as a 3-phase plan, then fitted to a 1–3 day free-trial run.",
         change="Document/SigNoz-POC-Simple-Plan.md (v2–v4).", valid="Plan approved.", lesson="Agree POC size before designing.", sev="Process"),
    dict(t="Free-trial vCPU quota: 4 per region, all families", where="Azure quota (az vm list-usage)", err="Total Regional vCPUs 0 / 4 in uksouth, ukwest, westeurope, northeurope; changing VM family does not help",
         cause="Free-trial subscriptions cap total regional vCPUs at 4.", steps="Checked usage in four regions.",
         fix="Split VMs across two regions: SigNoz VM (4 vCPU) in the main region, Windows support VM (2 vCPU) in a second region, joined by global VNet peering.",
         change="support_vm.tf (support VNet, peering, NSG, VM), dns.tf links, network.tf NSG rule 110.", valid="Both VMs created in India regions.",
         lesson="Check subscription quotas before choosing VM sizes.", sev="Blocking"),
    dict(t="VM capacity restrictions in UK South / UK West", where="terraform apply (poc-uksouth)",
         err="SkuNotAvailable: The requested VM size for resource 'Following SKUs have failed for Capacity Restrictions: Standard_B4ms' is currently not available in location 'uksouth'. (Also Standard_B2ms ukwest, then Standard_B4as_v2 uksouth and Standard_B2s_v2 ukwest.)",
         cause="Free-trial subscriptions are restricted from these sizes in UK regions.", steps="Tried B4ms/B2ms, then B4ls_v2 considered, then B4as_v2/B2s_v2; all refused. A portal test in India succeeded.",
         fix="Moved the deployment to Central India (+ South India for the support VM) using a new tfvars file and workspace; no code change.",
         change="environments/poc-centralindia.tfvars; VM size defaults B4as_v2 / B2s_v2.", valid="Both VMs running (B4as_v2 centralindia, B2s_v2 southindia).",
         lesson="Run production-like POCs on a pay-as-you-go subscription in the target region.", sev="Blocking"),
    dict(t="Azure SQL provisioning disabled in UK South", where="terraform apply (azurerm_mssql_server.main)",
         err="Status: \"ProvisioningDisabled\" … Subscriptions are restricted from provisioning in this region. Please choose a different region.",
         cause="Free-trial SQL region restriction.", steps="Error repeated on second apply (operation start 2026-09-29T19:57:49Z).",
         fix="Region move to Central India.", change="As issue 4.", valid="SQL database Online in centralindia.", lesson="Same as issue 4.", sev="Blocking"),
    dict(t="App Service B1 quota is zero", where="terraform apply (azurerm_service_plan.main)",
         err="401 Unauthorized … Operation cannot be completed without additional quota. Current Limit (B1 VMs): 0",
         cause="Free-trial App Service quota in UK South.", steps="Confirmed free tier F1 cannot use VNet integration or custom containers.",
         fix="Region move to Central India.", change="As issue 4.", valid="asp-sigpoc-poc-cin (B1) created; Web App running.", lesson="Same as issue 4.", sev="Blocking"),
    dict(t="terraform destroy found nothing to destroy", where="User terminal, poc-uksouth cleanup",
         err="No changes. No objects need to be destroyed. … Destroy complete! Resources: 0 destroyed.",
         cause="Creating the poc-centralindia workspace switched the active workspace for the folder; destroy ran against the empty India state with UK variables.",
         steps="terraform workspace list showed * poc-centralindia; UK state still held 55 entries.",
         fix="terraform workspace select poc-uksouth, then destroy.", change="None.", valid="UK resources destroyed.",
         lesson="Always run terraform workspace show before plan/apply/destroy.", sev="Operational"),
    dict(t="Saved plan file not readable", where="User terminal", err="“plan is not visible”",
         cause="Terminal was in the wrong folder, and .tfplan files are binary.", steps="Read the terminal; checked the saved plan.",
         fix="Exported with terraform show -no-color to docs/terraform-plan-poc-uksouth.txt; documented cd and terraform show.",
         change="None.", valid="Plan readable (72 resources).", lesson="Use terraform show to read saved plans.", sev="Minor"),
    dict(t="blobfuse2 and sqlcmd missing on the SigNoz VM", where="cloud-init (scripts/cloud-init-signoz.yaml)",
         err="which blobfuse2 sqlcmd → not found; apt: E: Unable to locate package sqlcmd",
         cause="The single apt-get line installed sqlcmd and blobfuse2 together; sqlcmd is not in the Ubuntu 24.04 Microsoft repo, so the whole command failed.",
         steps="Checked apt sources and apt-cache policy (blobfuse2 2.5.5 available).", fix="Installed blobfuse2 and fuse3 remotely; removed sqlcmd from cloud-init; added lifecycle ignore_changes = [custom_data] so editing cloud-init never recreates the VM.",
         change="scripts/cloud-init-signoz.yaml, signoz_vm.tf.", valid="/usr/bin/blobfuse2 present; mount working.", lesson="Install packages one per command in bootstrap scripts.", sev="Moderate"),
    dict(t="Image build failed: OpenTelemetry installer requires GitHub CLI", where="docker build (local)",
         err="The GitHub CLI ('gh') is required to verify release assets. Install it from https://cli.github.com/ or set SKIP_RELEASE_VERIFICATION=true to explicitly skip verification.",
         cause="Current otel-dotnet-auto-install.sh verifies release assets with gh; 'latest' also resolved to a moving target (v1.17.0).",
         steps="Captured full build log; confirmed latest release tag with curl.", fix="Pinned v1.17.0 and set SKIP_RELEASE_VERIFICATION=true for the installer.",
         change="app/Dockerfile.", valid="Build succeeded; installer downloaded v1.17.0 linux-glibc.", lesson="Pin agent versions; add proper verification for production images.", sev="Blocking"),
    dict(t="Obsolete auto-instrumentation environment variables", where="docker image inspection",
         err="ls: cannot access '/otel-dotnet-auto/AdditionalDeps': No such file or directory (also /store)",
         cause="v1.17 no longer ships AdditionalDeps or store; the Dockerfile copied older instrument.sh variables.",
         steps="Read /otel-dotnet-auto/instrument.sh in the image.", fix="Removed DOTNET_ADDITIONAL_DEPS and DOTNET_SHARED_STORE; kept CORECLR_* and DOTNET_STARTUP_HOOKS.",
         change="app/Dockerfile.", valid="Local run: traces, metrics, logs received; telemetry.distro.version 1.17.0.", lesson="Derive agent env vars from the installed version's instrument.sh.", sev="Moderate"),
    dict(t="Collector exited on start", where="Local Docker test (otelcol 0.135.0)",
         err="invalid configuration: extensions::file_storage: directory must exist: stat /var/lib/otelcol/storage: no such file or directory",
         cause="file_storage requires an existing directory.", steps="docker ps showed Exited (1); read logs.",
         fix="Added create_directory: true.", change="collector/otel-collector-config.yaml.", valid="Collector healthy; filelog parsed test lines.",
         lesson="Test collector configs locally before deploying.", sev="Blocking"),
    dict(t="Framework log noise", where="Local app test", err="Per-request info logs from Microsoft.AspNetCore.* and EF Core commands",
         cause="Default logging at Information for framework categories.", steps="Counted log categories in container output.",
         fix="appsettings.json: Microsoft.AspNetCore and Microsoft.EntityFrameworkCore at Warning.", change="app/src/DqLite.Api/appsettings.json.",
         valid="Only app and lifetime logs remain.", lesson="Set framework log levels before shipping logs to a paid or sized backend.", sev="Minor"),
    dict(t="ACR Tasks not permitted", where="app/deploy.sh (az acr build)",
         err="(TasksOperationsNotAllowed) ACR Tasks requests for the registry crsigpocpocxxxxx and &lt;subscription-id&gt; are not permitted.",
         cause="ACR Tasks are blocked on free-trial subscriptions.", steps="—",
         fix="deploy.sh now builds locally (docker build --platform linux/amd64), az acr login, docker push; --acr keeps the cloud build option.",
         change="app/deploy.sh.", valid="crsigpocpocxxxxx.azurecr.io/dqlite-api:v1 pushed (digest sha256:003a8229…).", lesson="Keep a local-build path for restricted subscriptions.", sev="Blocking"),
    dict(t="SigNoz Docker Compose install deprecated", where="SigNoz repository v0.143.0 deploy/README.md",
         err="The install.sh script and the docker-compose manifests have been deprecated. SigNoz now installs and runs through Foundry.",
         cause="SigNoz changed its installer.", steps="Read deploy/README.md and MIGRATION.md; read signoz.io/docs/install/docker.",
         fix="Installed foundryctl; wrote signoz/casting.yaml; forge first to inspect, then cast.", change="signoz/casting.yaml (new).",
         valid="All containers healthy; UI 200; /api/v1/health ok.", lesson="Base runbooks on Foundry.", sev="Moderate"),
    dict(t="Port clash on 4317/4318 and unpinned ingester", where="Generated pours/deployment/compose.yaml",
         err="ingester: image signoz/signoz-otel-collector:latest; ports 4317:4317, 4318:4318 (already used by our collector)",
         cause="Foundry defaults publish the ingester's OTLP ports and use latest.", steps="Inspected forge output before cast.",
         fix="JSON-patch operations: remove ingester ports; pin ingester and migrator to v0.144.11; ClickHouse mem_limit 8g.",
         change="signoz/casting.yaml patches.", valid="Only 8080 published; compose config valid.", lesson="Always forge and inspect before cast.", sev="Moderate"),
    dict(t="Collector could not reach the SigNoz ingester", where="otelcol logs / SigNoz logs",
         err="grpc: addrConn.createTransport failed to connect to {Addr: \"ingester:4317\"} … connection refused; SigNoz: \"failed to find or create agent\"",
         cause="The ingester only starts its OTLP receiver after SigNoz pushes configuration over OpAMP, which needs an organisation; none exists until the first admin signs up.",
         steps="Confirmed both containers on signoz-network; TCP test to the ingester IP:4317 refused; read OpAMP errors in signoz-signoz-0.",
         fix="First admin sign-up in the UI from the support VM.", change="None (operational step).",
         valid="Port 4317 open; 0 connection failures; 163 spans, 98 logs, 49 Blob logs in ClickHouse.", lesson="Sign-up is a mandatory install step before ingestion.", sev="Blocking"),
    dict(t="Event Hub and Azure Monitor auth not supported as configured", where="otelcol validate (0.135.0)",
         err="'auth' expected a map or struct, got \"string\"; 'extensions' unknown type: \"azure_auth\" … (valid values: … azureauth …)",
         cause="In 0.135.0 azuremonitor uses auth.authenticator, and azureeventhub supports only a connection string. Managed-identity auth for Event Hub exists in newer releases.",
         steps="Read v0.135.0 READMEs; checked main-branch README and latest releases (0.161.0 on 15 Sept, 0.162.0 on 29 Sept).",
         fix="Upgraded to otel/opentelemetry-collector-contrib:0.161.0; azure_auth extension with managed_identity; azure_event_hub with auth and event_hub.namespace; azure_monitor with auth.authenticator. Renamed azuremonitor → azure_monitor after a deprecation warning.",
         change="collector/otel-collector-config.yaml, collector/docker-compose.yaml, collector/.env.example.",
         valid="validate exit 0; 156 azure_* metric names in ClickHouse.", lesson="Use collector ≥ 0.161 for keyless Azure ingestion.", sev="Moderate"),
    dict(t="Event Hub received zero diagnostic logs", where="Event Hub metrics / SigNoz logs",
         err="IncomingMessages 0.0; Event Hub logs in SigNoz: 0",
         cause="The namespace had public access disabled without the trusted Microsoft services bypass, so diagnostic settings could not deliver. No error is surfaced anywhere.",
         steps="Queried namespace metrics by resource ID; confirmed diagnostic settings enabled (allLogs); confirmed the collector had no auth errors.",
         fix="network_rulesets { default_action = \"Deny\", public_network_access_enabled = false, trusted_service_access_enabled = true }.",
         change="deploy/terraform/azure/infra/eventhub.tf (plan: 0 add, 3 change, 0 destroy).",
         valid="Incoming messages observed; SigNoz logs: AppServiceConsoleLogs 155, AppServiceHTTPLogs 21, DatabaseWaitStatistics 1.",
         lesson="Mandatory setting for every private Event Hub used by diagnostic settings.", sev="Blocking"),
    dict(t="SigNoz Infrastructure → Hosts page empty", where="SigNoz UI instrumentation checks",
         err="Missing default metrics: system.cpu.time, system.memory.usage, system.cpu.load_average.15m, system.filesystem.usage (hostmetricsreceiver). Missing required attributes: host.name (resourcedetectionprocessor).",
         cause="No host metrics were collected.", steps="Read the UI checks.",
         fix="Added hostmetrics (root_path /hostfs) and resourcedetection/host (env, azure, system) in a separate metrics/host pipeline; mounted / at /hostfs read-only and pid: host.",
         change="collector/otel-collector-config.yaml, collector/docker-compose.yaml.",
         valid="All four metrics present; host.name = vm-signoz-sigpoc-poc-cin, cloud.platform = azure.vm.", lesson="Include host metrics for the observability VM itself.", sev="Minor"),
]
SEV_CLASS = {"Blocking": "bad", "Moderate": "warn", "Minor": "info", "Operational": "az", "Process": "az"}


def issue_html(i, it):
    rows = [("Where it occurred", it["where"]), ("Error message", f"<code>{html.escape(it['err'])}</code>"),
            ("Root cause", it["cause"]), ("Investigation", it["steps"]), ("Resolution", it["fix"]),
            ("Changed", it["change"]), ("Validation", it["valid"]), ("Lesson learned", it["lesson"])]
    dl = "".join(f"<dt>{k}</dt><dd>{v if k == 'Error message' else html.escape(v)}</dd>" for k, v in rows)
    return (f'<details class="issue"><summary><span class="id">#{i}</span><span class="t">{html.escape(it["t"])}</span>'
            f'<span class="pill {SEV_CLASS[it["sev"]]}">{it["sev"]}</span></summary><div class="body"><dl>{dl}</dl></div></details>')


summary_rows = "".join(
    f"<tr><td class='num'>{i}</td><td>{html.escape(it['t'])}</td><td>{html.escape(it['where'])}</td>"
    f"<td><span class='pill {SEV_CLASS[it['sev']]}'>{it['sev']}</span></td><td><span class='pill ok'>Resolved</span></td></tr>"
    for i, it in enumerate(ISSUES, 1))
ISSUES_HTML = (
    '<div class="tbl"><table><thead><tr><th class="num">#</th><th>Issue</th><th>Where</th><th>Severity</th><th>Status</th></tr></thead>'
    f'<tbody>{summary_rows}</tbody></table></div>'
    '<p><button type="button" id="expandAll" class="xbtn">Expand all</button></p>'
    + "".join(issue_html(i, it) for i, it in enumerate(ISSUES, 1)))

SCRIPT = """
const INFO = %s;
const root = document.getElementById('arch');
const panel = document.getElementById('dinfo');
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function show(id){
  const d = INFO[id]; if(!d) return;
  root.querySelectorAll('.node.sel').forEach(n=>n.classList.remove('sel'));
  root.querySelectorAll('[data-id="'+id+'"]').forEach(n=>n.classList.add('sel'));
  panel.innerHTML = '<h4>'+esc(d.t)+'</h4><p>'+esc(d.d)+'</p>';
}
root.addEventListener('click', e=>{const n=e.target.closest('.node'); if(n) show(n.dataset.id);});
root.addEventListener('keydown', e=>{ if((e.key==='Enter'||e.key===' ') && e.target.classList && e.target.classList.contains('node')){e.preventDefault(); show(e.target.dataset.id);} });
root.querySelectorAll('.dtabs button').forEach(b=>b.addEventListener('click',()=>{
  root.querySelectorAll('.dtabs button').forEach(x=>x.setAttribute('aria-selected', x===b?'true':'false'));
  root.querySelectorAll('.dcanvas').forEach(c=>{c.hidden = c.dataset.v!==b.dataset.view;});
  try{localStorage.setItem('signozpoc-view', b.dataset.view);}catch(_){}
}));
try{const v=localStorage.getItem('signozpoc-view'); const b=v&&root.querySelector('.dtabs button[data-view="'+v+'"]'); if(b) b.click();}catch(_){}
const xb=document.getElementById('expandAll');
if(xb) xb.addEventListener('click',()=>{const all=[...document.querySelectorAll('details.issue')]; const open=!all.every(d=>d.open); all.forEach(d=>d.open=open); xb.textContent=open?'Collapse all':'Expand all';});
""" % json.dumps(INFO)

tpl = (HERE / "report.template.html").read_text()
tpl = tpl.replace("{{DIAGRAM}}", DIAGRAM).replace("{{ISSUES}}", ISSUES_HTML).replace("{{SCRIPT}}", SCRIPT)
tpl = tpl.replace("</style>", ".xbtn{font:600 13px var(--f-body);border:1px solid var(--rule);background:var(--paper);color:var(--ink);"
                  "padding:6px 12px;border-radius:6px;cursor:pointer}.xbtn:focus-visible{outline:2px solid var(--azure)}\n</style>", 1)
OUT.write_text(tpl)
print(OUT, f"{OUT.stat().st_size/1024:.0f} KB")

# Standalone architecture page: same styles, diagram and flows only.
style = tpl[:tpl.index("</style>") + len("</style>")]
flows = tpl[tpl.index('<div class="grid2">', tpl.index('id="s14"')):tpl.index('<!-- ============================================================ 15 -->')]
arch = (style.replace("<title>SigNoz POC on Azure</title>", "<title>SigNoz POC Architecture</title>")
        + '<main style="max-width:1280px;margin:0 auto;border:0">'
        + '<div class="eyebrow">Azure Observability · Proof of Concept</div><h1>SigNoz POC architecture</h1>'
        + '<p class="lede">Final implemented architecture. Choose a view and click any component for its configuration. '
        + 'Full write-up: <a href="signoz-poc-report.html">signoz-poc-report.html</a>.</p>'
        + DIAGRAM + "<h2>Flows</h2>" + flows + "</main><script>" + SCRIPT.replace(
            "const xb=document.getElementById('expandAll');", "const xb=null;") + "</script>")
ARCH = HERE.parent / "architecture.html"
ARCH.write_text(arch)
print(ARCH, f"{ARCH.stat().st_size/1024:.0f} KB")
