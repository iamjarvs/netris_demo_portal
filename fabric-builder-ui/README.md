# Netris Fabric Terraform Builder UI

A modern visual design and code-generation tool for building production-ready **Netris Day-0 Terraform & OpenTofu deployments**.

Built strictly in accordance with **`common-ui-guidelines`** (Forced Light Theme, Coral `#FF3366` palette, Outfit typography, TailAdmin v2 app shell, zero vendor branding) and the architectural patterns of live deployments (`msp2`, `chl2`, `kpn01`, `tus2`).

---

## Key Capabilities

### 1. Multi-Plane Backend RoCE Fabric Designer
- **Single Plane (1)**: Standard East-West Spine-Leaf fabric for GPU compute clusters.
- **Dual Plane (2)**: Dual independent East-West fabrics (Plane 1 & Plane 2). GPU RoCE interfaces are striped 50/50 across both planes for multi-rail resilience.
- **Quad Plane (4)**: Four independent East-West Clos fabrics. GPU interfaces are striped evenly (e.g. 4 RoCE ports per plane) for ultra-dense cluster scale and zero cross-plane contention.
- **Dynamic Sizing**: Configure Spine count, Leaf count, switch port density (32/64/128p), NOS (`cumulus_nvue`, `sonic`, `arista_eos`), leaf breakouts, and GPU fleet size.

### 2. Frontend, Storage & Out-of-Band Networks
- **North-South (NS) Fabric**: Spines, Leaves, border Softgates (`sg-hs`, `sg-std`), inband management VPC and V-Net.
- **Dedicated Storage Fabric**: Optional dedicated storage leaf tier, NVMe-oF/RoCE storage nodes, and storage V-Net.
- **Dedicated Out-of-Band (OOB) Fabric**: Optional dedicated management fabric with DHCP scopes (`purpose = "management"`) and OOB VPC.

### 3. Live Netris Controller Pre-Flight & Conflict Engine
- **Live State Discovery**: Connects to any Netris Controller (e.g., `https://adam-ctl.netris.io`) via session authentication.
- **CIDR Overlap Detection**: Uses Python `ipaddress` network intersection logic to check proposed loopback, P2P, mgmt, and storage subnets against existing controller allocations and subnets.
- **Intelligent Pool Recommender**: When collisions occur, the engine calculates the next contiguous, non-overlapping RFC1918 CIDR block.
- **ASN Collision Prevention**: Validates site ASN, RoH ASN, and switch ASNs against live BGP peers and existing sites, proposing the next available ASN.
- **Naming Conflict Guard**: Detects naming collisions across Sites, Switches, Servers, and V-Nets.
- **1-Click Auto-Fix**: The "Apply All Suggested Alternatives" button adopts all non-overlapping pools and increments conflicting names instantly.

### 4. Production OpenTofu / Terraform Generation
- Generates standard, modular Day-0 files:
  - `terraform.tf` (Netris provider configuration, data sources, site resource)
  - `terraform.tfvars` (Per-site parameters, controller creds, ASNs, NTP, DNS, timezone)
  - `inventory_profile.tf` (Spectrum-X RoCE profile, North-South profile, OOB profile)
  - `ipam.tf` & `csv/ipam.csv` (Root allocations and functional subnets)
  - `switches.tf` & `csv/switches.csv`
  - `softgates.tf` & `csv/softgates.csv`
  - `servers_gpu.tf` & `csv/servers_gpu.csv`
  - `servers_storage.tf` & `csv/servers_storage.csv` (if storage enabled)
  - `servers_mgmt.tf` & `csv/servers_mgmt.csv`
  - `vpc.tf` & `vnets.tf` & `csv/vnets.csv`
  - `links_ew_switch.tf`, `links_ew_gpu.tf`, `links_ns_*.tf`, `links_storage.tf`, `links_softgate.tf`
  - `breakouts.tf` & `csv/breakouts.csv`
  - `README.md` (Deployment runbook)
- **In-App Syntax Validation**: Runs local `/opt/homebrew/bin/tofu validate` and displays terminal output directly in the browser.
- **One-Click Download**: Generates and downloads an uncorrupted `.zip` bundle ready for `tofu init && tofu plan`.

---

## Quick Start

### Option A: One-Click Launch (Recommended)
Run the startup script:
```bash
./start.sh
```
This checks dependencies, verifies the frontend build, boots the server on port `5050`, and opens your default browser at `http://localhost:5050`.

### Option B: Development Mode (Vite Hot-Reload)
Run the backend and frontend separately:

1. **Start Backend**:
   ```bash
   cd backend
   python3 app.py
   ```
   Backend listens on `http://localhost:5050`.

2. **Start Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend Vite dev server boots on `http://localhost:5173` with automatic API proxying to port 5050.

---

## Directory Structure

```
fabric-builder-ui/
├── start.sh                 # One-click startup script
├── README.md                # Documentation & usage guide
├── backend/
│   ├── app.py               # Flask REST API server & static asset host
│   ├── netris_client.py     # Live Netris Controller REST API client
│   ├── conflict_engine.py   # IPAM, ASN, and naming conflict & recommendation engine
│   └── tf_generator.py      # Day-0 OpenTofu HCL and CSV generation engine
└── frontend/
    ├── index.html           # HTML template with Outfit font & light theme
    ├── vite.config.js       # Vite configuration with Tailwind v4 plugin
    ├── package.json
    └── src/
        ├── index.css        # Tailwind v4 theme with Coral palette tokens
        ├── main.jsx         # React application entrypoint
        ├── App.jsx          # Root layout shell & state coordinator
        └── components/
            ├── Sidebar.jsx             # TailAdmin v2 290px left navigation
            ├── Header.jsx              # Sticky header with breadcrumbs & actions
            ├── TopologyDesignView.jsx  # Single / Dual / Quad plane builder
            ├── FrontendStorageView.jsx # North-South, Storage & OOB network config
            ├── IpamControllerView.jsx  # Controller connection & IPAM inputs
            ├── ConflictInspectorView.jsx # Live conflict table & 1-click auto-fix
            ├── TerraformExportView.jsx # In-browser file viewer & OpenTofu validator
            └── DeployConsoleView.jsx   # Live OpenTofu Deployment & Teardown Console

---

### 5. Live Deployment & Teardown Console (OpenTofu CLI)
- **Built-in OpenTofu Pipeline**: Execute `tofu init`, `tofu plan`, and `tofu apply` directly from the browser against the live Netris Controller.
- **Real-Time Streaming Output**: View color-coded terminal logs and plan calculations (`+add / ~change / -destroy`) as OpenTofu runs.
- **State & Recovery Center**:
  - **Live State Inspection**: Reads `terraform.tfstate` to track exact resource counts, types, and instance counts in real time.
  - **Teardown / Cleanup Deployment (`tofu destroy`)**: Tears down completed or partially created resources from the Netris Controller in reverse dependency order, cleaning up failed runs.
  - **Local Workspace Reset**: Purges local `.tfstate`, plans, and locks for a clean slate without touching the controller.

