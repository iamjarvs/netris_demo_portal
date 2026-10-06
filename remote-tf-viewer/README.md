# Remote Terraform Viewer (VS Code Remote - SSH)

Quick utility tool to inspect and edit the live Day-0 Terraform manifests deployed on the active Netris Controller (`adam-ctl.netris.io`).

## Target Remote Device

- **Remote Host:** `ubuntu@adam-ctl.netris.io`
- **Remote Directory:** `~/netris-init/netris-spectrum-x-init` (`/home/ubuntu/netris-init/netris-spectrum-x-init`)
- **SSH Authentication:** `ubuntu` via configured SSH Key (`~/.ssh/id_ed25519` / `~/.ssh/id_rsa_work`)
- **Netris Controller Web:** `https://adam-ctl.netris.io`
- **Netris Web/API Username:** `netris` (or `admin`)
- **Netris Web/API Password:** `913QGAi6oQTSGgZm20eU`

## Command

The tool triggers VS Code's Remote - SSH extension in the background:

```bash
code --remote ssh-remote+<HOST> <REMOTE_PATH>
```

Specifically:

```bash
code --remote ssh-remote+ubuntu@adam-ctl.netris.io /home/ubuntu/netris-init/netris-spectrum-x-init
```

## Quick Start

Run the launcher from this folder:

```bash
./run.sh
```

Or run with connectivity check:

```bash
python3 open_tf.py --check
```

Or use the direct bash script:

```bash
./open_vscode.sh
```

## Remote Manifests

The remote folder contains:
- `bgp.tf`: eBGP sessions & peerings
- `east-west.tf`: Spine/Leaf fabric VPC & V-Net configurations
- `north-south.tf`: SoftGate border routing & upstream peering
- `server-cluster-template.tf`: GPU/Compute server templates
- `terraform.tf`: Netris provider declarations
- `terraform.tfvars`: Deployment variables & site settings
