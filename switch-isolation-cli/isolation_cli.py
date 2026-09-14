#!/usr/bin/env python3
"""
Switch Isolation CLI Utility Demo
An interactive, keyboard-navigated CLI showcasing various modern terminal menu styles
for managing and verifying switch isolation capabilities in enterprise & AI fabrics.
"""

import sys
import time
from typing import List
import questionary
from questionary import Choice, Separator, Style
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style as PtStyle
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box

console = Console()

# Custom Questionary styling matching modern developer tooling
custom_style = Style([
    ("qmark", "fg:#00d7af bold"),           # Cyan question mark
    ("question", "bold fg:#ffffff"),        # Bold white question text
    ("answer", "fg:#00ffff bold"),          # Cyan answered text
    ("pointer", "fg:#00d7af bold"),         # Cyan arrow pointer
    ("highlighted", "fg:#00d7af bold"),     # Selected item color
    ("selected", "fg:#00d7af"),             # Checkbox selected
    ("separator", "fg:#6c6c6c"),            # Dim separator lines
    ("instruction", "fg:#8a8a8a italic"),   # Subdued instructions
    ("text", "fg:#e4e4e4"),                 # Default text
    ("disabled", "fg:#585858 italic")       # Disabled items
])


def print_banner():
    console.clear()
    banner_text = Text()
    banner_text.append("⚡ SWITCH ISOLATION CLI UTILITY\n", style="bold cyan")
    banner_text.append("Interactive Menu & Navigation Patterns Showcase\n", style="italic white")
    banner_text.append("Simulating L2/L3 Multi-Tenancy & Hardware Fabric Isolation", style="dim")
    console.print(
        Panel(
            banner_text,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


# ----------------------------------------------------------------------
# 1. Standard Arrow-Key Select Menu (with Descriptions & Groups)
# ----------------------------------------------------------------------
def demo_arrow_select():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 1: Arrow Navigation with Groups & Descriptions[/bold green]\n"
        "• Navigate using [cyan]↑ / ↓[/cyan] arrow keys (or [cyan]j / k[/cyan])\n"
        "• Notice category separators and contextual descriptions below each selection",
        border_style="green",
        box=box.SIMPLE
    ))

    choices = [
        Separator("── Top-of-Rack / Leaf Switches ──────────────────────"),
        Choice(
            title="leaf-01  (NVIDIA Spectrum-3 SN3700C - 32x100GbE)",
            value="leaf-01",
            description="Tenant Compute Pod A - Hardware VXLAN & RoCEv2 Enabled"
        ),
        Choice(
            title="leaf-02  (Edgecore AS7712 - 32x100GbE)",
            value="leaf-02",
            description="Tenant Compute Pod B - L2/L3 Boundary Leaf"
        ),
        Choice(
            title="leaf-03  (Celestica DX010 - 32x100GbE)",
            value="leaf-03",
            description="Storage & AI GPU Ingestion - Dedicated VLAN Pool"
        ),
        Separator("── Spine & Super-Spine Fabrics ──────────────────────"),
        Choice(
            title="spine-01 (NVIDIA Spectrum-4 SN5600 - 64x800GbE)",
            value="spine-01",
            description="Core Fabric Transport - Non-blocking ECMP Core"
        ),
        Choice(
            title="spine-02 (Arista 7060X - 32x100GbE)",
            value="spine-02",
            description="Out-of-Band & Management Transit Aggregation"
        ),
        Separator("─────────────────────────────────────────────────────"),
        Choice(title="« Back to Main Menu", value="back")
    ]

    selected = questionary.select(
        "Select switch to inspect isolation capabilities:",
        choices=choices,
        style=custom_style,
        use_arrow_keys=True,
        use_jk_keys=True,
        show_description=True,
    ).ask()

    if selected and selected != "back":
        console.print(f"\n[bold cyan]Selected Device:[/bold cyan] [white]{selected}[/white]")
        
        # Display sample switch details
        table = Table(title=f"Hardware Isolation Profile: {selected}", box=box.ROUNDED)
        table.add_column("Capability", style="cyan", no_wrap=True)
        table.add_column("Hardware Mechanism", style="magenta")
        table.add_column("Max Isolated Domains", style="yellow")
        table.add_column("Current Status", style="green")

        table.add_row("L2 Broadcast Domain", "V-Net / VXLAN VNI Mapping", "4,094 VNIs", "Strict Isolation (Active)")
        table.add_row("L3 Routing Plane", "VRF-Lite / Multi-VRF Routing", "256 VRFs", "Zero Route Leakage")
        table.add_row("Hardware Access Control", "Ingress/Egress TCAM ACLs", "32,768 Entries", "Default Deny")
        table.add_row("Port Micro-Segmentation", "Private VLAN / Isolated Ports", "Per-port bitmap", "Enabled (Port 1-24)")
        console.print(table)
    
    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


# ----------------------------------------------------------------------
# 2. Live Search & Fuzzy Filter Menu
# ----------------------------------------------------------------------
def demo_search_filter():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 2: Live Search & Fuzzy Filter Menu[/bold green]\n"
        "• Just start typing (e.g. [yellow]'gpu'[/yellow], [yellow]'tenant-b'[/yellow], [yellow]'eth1/12'[/yellow], or [yellow]'isolated'[/yellow])\n"
        "• Filters immediately across dozens of ports and segments in real time\n"
        "• Use [cyan]↑ / ↓[/cyan] to navigate the filtered results and [cyan]Enter[/cyan] to pick",
        border_style="green",
        box=box.SIMPLE
    ))

    # 25+ realistic switch ports and virtual network segments
    port_pool = [
        Choice("eth1/1  - Tenant-A (Production Web) [V-Net 101, VLAN 10]", value="eth1/1"),
        Choice("eth1/2  - Tenant-A (Database Cluster) [V-Net 101, VLAN 11]", value="eth1/2"),
        Choice("eth1/3  - Tenant-A (Internal Storage) [V-Net 101, VLAN 12]", value="eth1/3"),
        Choice("eth1/4  - Tenant-B (Staging Services) [V-Net 201, VLAN 20]", value="eth1/4"),
        Choice("eth1/5  - Tenant-B (QA Environments) [V-Net 201, VLAN 21]", value="eth1/5"),
        Choice("eth1/6  - Tenant-C (AI Research Cluster 01) [GPU V-Net 301, VLAN 30]", value="eth1/6"),
        Choice("eth1/7  - Tenant-C (AI Research Cluster 02) [GPU V-Net 301, VLAN 30]", value="eth1/7"),
        Choice("eth1/8  - Tenant-C (GPU Training Node 01) [NVLink/RoCEv2 Isolated]", value="eth1/8"),
        Choice("eth1/9  - Tenant-C (GPU Training Node 02) [NVLink/RoCEv2 Isolated]", value="eth1/9"),
        Choice("eth1/10 - Tenant-D (OOB Management Node) [V-Net 401, Isolated VRF]", value="eth1/10"),
        Choice("eth1/11 - Tenant-D (Telemetry Collectors) [V-Net 401, Isolated VRF]", value="eth1/11"),
        Choice("eth1/12 - DMZ / SoftGate Transit Port 01 [Isolated L3 Uplink]", value="eth1/12"),
        Choice("eth1/13 - DMZ / SoftGate Transit Port 02 [Isolated L3 Uplink]", value="eth1/13"),
        Choice("eth1/14 - Isolated Lab Sandbox A [Strict Port Isolation, PVLAN]", value="eth1/14"),
        Choice("eth1/15 - Isolated Lab Sandbox B [Strict Port Isolation, PVLAN]", value="eth1/15"),
        Choice("eth1/16 - Backup Network / Replication Target [V-Net 500]", value="eth1/16"),
        Choice("eth1/17 - Edge Gateway BGP Peering Port [Filtered ACL]", value="eth1/17"),
        Choice("eth1/18 - Unassigned / Quarantined Port [Hardware Admin Down]", value="eth1/18"),
        Choice("« Back to Main Menu", value="back")
    ]

    selected_port = questionary.select(
        "Type to filter and search interface/tenant:",
        choices=port_pool,
        style=custom_style,
        use_search_filter=True,  # Enables type-ahead real-time filtering!
        use_jk_keys=False,
    ).ask()

    if selected_port and selected_port != "back":
        console.print(f"\n[bold green]Inspecting Port:[/bold green] [bold cyan]{selected_port}[/bold cyan]")
        
        info_panel = Panel(
            f"[bold white]Interface:[/bold white] {selected_port}\n"
            f"[bold white]L2 Isolation Mode:[/bold white] Isolated Private VLAN (No inter-port L2 forwarding)\n"
            f"[bold white]L3 VRF Context:[/bold white] Isolated Tenant VRF\n"
            f"[bold white]Hardware Filter:[/bold white] Ingress TCAM Drop Rule active for untrusted subnets\n"
            f"[bold white]Cross-Tenant Leakage Risk:[/bold white] [bold green]ZERO (Hardware Verified)[/bold green]",
            title="Interface Isolation Parameters",
            border_style="cyan"
        )
        console.print(info_panel)

    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


# ----------------------------------------------------------------------
# 3. Autocomplete & Suggestion Input
# ----------------------------------------------------------------------
def demo_autocomplete():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 3: Autocomplete with Dropdown Suggestions[/bold green]\n"
        "• Press [cyan][Tab][/cyan] or start typing to see completion candidates\n"
        "• Includes contextual metadata shown beside each suggestion\n"
        "• Try typing [yellow]'v'[/yellow] for V-Nets or [yellow]'10.'[/yellow] for subnets",
        border_style="green",
        box=box.SIMPLE
    ))

    suggestions = [
        "vnet-prod-web",
        "vnet-prod-db",
        "vnet-gpu-training",
        "vnet-ai-inference",
        "vnet-dmz-external",
        "vnet-storage-nvme",
        "10.100.10.0/24 (Tenant-A)",
        "10.100.20.0/24 (Tenant-B)",
        "10.200.0.0/16  (AI Fabric Private Subnet)",
        "172.16.50.0/24 (OOB Management)"
    ]

    meta_info = {
        "vnet-prod-web": "VPC-101 | EVPN VNI 100101 | Isolated L3",
        "vnet-prod-db": "VPC-101 | EVPN VNI 100102 | Non-Routable",
        "vnet-gpu-training": "VPC-201 | RoCEv2 Lossless | Strict Isolation",
        "vnet-ai-inference": "VPC-201 | Low-latency Inference Pool",
        "vnet-dmz-external": "VPC-999 | SoftGate Managed Transit",
        "vnet-storage-nvme": "VPC-101 | NVMe-oF Dedicated RDMA",
        "10.100.10.0/24 (Tenant-A)": "VLAN 10 | Gateway on SoftGate",
        "10.100.20.0/24 (Tenant-B)": "VLAN 20 | Gateway on SoftGate",
        "10.200.0.0/16  (AI Fabric Private Subnet)": "Jumbo Frames 9216 | Isolated",
        "172.16.50.0/24 (OOB Management)": "Dedicated OOB VRF"
    }

    entered = questionary.autocomplete(
        "Enter or Tab-complete a Virtual Network / Subnet to test:",
        choices=suggestions,
        meta_information=meta_info,
        complete_style=CompleteStyle.COLUMN,
        style=custom_style
    ).ask()

    if entered:
        console.print(f"\n[bold cyan]Selected Domain:[/bold cyan] [bold white]{entered}[/bold white]")
        console.print(f"[dim]Lookup Metadata:[/dim] {meta_info.get(entered, 'Custom entry')}\n")

    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


# ----------------------------------------------------------------------
# 4. Multi-Select Checkbox Menu
# ----------------------------------------------------------------------
def demo_checkbox():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 4: Multi-Select Checkbox Menu[/bold green]\n"
        "• Use [cyan]↑ / ↓[/cyan] to navigate\n"
        "• Press [cyan][Space][/cyan] to toggle an item on/off\n"
        "• Press [cyan][a][/cyan] to toggle all, [cyan][Enter][/cyan] when finished",
        border_style="green",
        box=box.SIMPLE
    ))

    capabilities = [
        Choice(
            title="Hardware L2 Isolation (EVPN / VXLAN VNI Segregation)",
            value="l2_vxlan",
            checked=True
        ),
        Choice(
            title="L3 Multi-VRF Routing Isolation (Zero Inter-VRF Leakage)",
            value="l3_vrf",
            checked=True
        ),
        Choice(
            title="Port Micro-Segmentation (Private VLAN Port Isolation)",
            value="pvlan",
            checked=False
        ),
        Choice(
            title="Hardware TCAM ACL Rules (Hardware Wire-speed Drop)",
            value="tcam_acl",
            checked=True
        ),
        Choice(
            title="SoftGate Stateful Inspection & NAT Gateway Isolation",
            value="softgate",
            checked=False
        ),
        Choice(
            title="RoCEv2 / InfiniBand Partition Key (pKey) Multi-Tenancy",
            value="pkey",
            checked=False
        ),
        Choice(
            title="BGP EVPN Route Target (RT) Community Separation",
            value="evpn_rt",
            checked=True
        )
    ]

    selected_caps = questionary.checkbox(
        "Select isolation features to enforce on the switch fabric:",
        choices=capabilities,
        style=custom_style
    ).ask()

    if selected_caps is not None:
        console.print("\n[bold cyan]Enforced Isolation Policies:[/bold cyan]")
        for cap in selected_caps:
            console.print(f"  [green]✔[/green] Enforced: [bold white]{cap}[/bold white]")

    questionary.press_any_key_to_continue("\nPress any key to return to menu...").ask()


# ----------------------------------------------------------------------
# 5. Full End-to-End Switch Isolation Workflow Simulation
# ----------------------------------------------------------------------
def demo_full_workflow():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 5: End-to-End Switch Isolation Workflow[/bold green]\n"
        "Chaining menus together: Select Source -> Select Target -> Select Policy -> Live Test",
        border_style="green",
        box=box.SIMPLE
    ))

    # Step 1: Switch Selection
    switch = questionary.select(
        "Step 1: Select switch under test:",
        choices=[
            "leaf-01 (NVIDIA Spectrum-3 SN3700C)",
            "leaf-02 (Edgecore AS7712)",
            "leaf-03 (Celestica DX010)",
        ],
        style=custom_style
    ).ask()

    if not switch:
        return

    # Step 2: Source Tenant Port
    source_tenant = questionary.select(
        "Step 2: Select Source Tenant & Interface:",
        choices=[
            Choice("Tenant-Alpha: GPU Worker 01 (Port 1/1, V-Net 101)", value=("Tenant-Alpha", "10.10.1.5", "Port 1/1")),
            Choice("Tenant-Alpha: Storage Client (Port 1/2, V-Net 101)", value=("Tenant-Alpha", "10.10.1.6", "Port 1/2")),
            Choice("Tenant-Beta: Training Node 01 (Port 1/5, V-Net 202)", value=("Tenant-Beta", "10.20.1.5", "Port 1/5")),
        ],
        style=custom_style
    ).ask()

    if not source_tenant:
        return

    # Step 3: Destination Tenant Port
    dest_tenant = questionary.select(
        "Step 3: Select Target Destination to attempt communication:",
        choices=[
            Choice("Tenant-Beta: Production DB (Port 1/6, V-Net 202)", value=("Tenant-Beta", "10.20.1.8", "Port 1/6")),
            Choice("Tenant-Gamma: Confidential AI Model (Port 1/12, V-Net 303)", value=("Tenant-Gamma", "10.30.1.10", "Port 1/12")),
            Choice("Shared Infrastructure: Core DNS/NTP (Port 1/32, Common V-Net)", value=("Infra-Shared", "192.168.1.1", "Port 1/32")),
        ],
        style=custom_style
    ).ask()

    if not dest_tenant:
        return

    # Step 4: Isolation Mechanism Test
    test_type = questionary.select(
        "Step 4: Select Isolation Vector to verify:",
        choices=[
            "L2 Broadcast / ARP Probe (Broadcast Domain Boundary)",
            "L3 Unicast IP Routing (VRF Route Table Inspection)",
            "Direct Port-to-Port Cross-Talk (ASIC Hardware Table Check)",
            "TCAM ACL Egress Filtering (Policy Drop Verification)"
        ],
        style=custom_style
    ).ask()

    if not test_type:
        return

    # Live simulation output with Rich
    console.print("\n[bold yellow]Running Hardware Isolation Verification on Switch...[/bold yellow]")
    with console.status("[bold cyan]Injecting test probe packets & inspecting hardware ASICs...[/bold cyan]", spinner="dots"):
        time.sleep(1.2)

    # Render Result Tree
    tree = Tree(f"[bold white]Switch Hardware Isolation Results: {switch}[/bold white]")
    src_branch = tree.add(f"[bold cyan]Source:[/bold cyan] {source_tenant[0]} ({source_tenant[1]} via {source_tenant[2]})")
    dst_branch = tree.add(f"[bold magenta]Destination:[/bold magenta] {dest_tenant[0]} ({dest_tenant[1]} via {dest_tenant[2]})")
    test_branch = tree.add(f"[bold yellow]Test Vector:[/bold yellow] {test_type}")

    if source_tenant[0] != dest_tenant[0] and dest_tenant[0] != "Infra-Shared":
        res_branch = tree.add("[bold green]STATUS: COMPLETE HARDWARE ISOLATION ENFORCED[/bold green]")
        res_branch.add("ASIC L2 Table: No MAC cross-population across VNIs")
        res_branch.add("L3 FIB: Distinct VRF routing tables; 0 leaked routes")
        res_branch.add("TCAM Counter: Packets Dropped = 100% (Wire-speed drop)")
        result_style = "bold green"
        verdict = "PASSED - ZERO TRAFFIC LEAKAGE"
    else:
        res_branch = tree.add("[bold yellow]STATUS: CONTROLLED ACCESS VIA ROUTED POLICY[/bold yellow]")
        res_branch.add("Route permitted via Netris SoftGate Transit Rule")
        result_style = "bold yellow"
        verdict = "AUTHORIZED ACCESS ONLY"

    console.print()
    console.print(Panel(tree, border_style="cyan", title="Hardware Verification Summary"))
    console.print(f"[{result_style}]>>> Final Verdict: {verdict}[/{result_style}]\n")

    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


# ----------------------------------------------------------------------
# 6. Hybrid Showcase: Combining Arrow Navigation + Autocomplete
# ----------------------------------------------------------------------
def demo_hybrid_arrow_autocomplete():
    print_banner()
    console.print(Panel.fit(
        "[bold green]Menu Style 6: Hybrid Arrow Navigation + Autocomplete[/bold green]\n"
        "Yes! Combining both is the gold standard for high-productivity CLIs.\n"
        "Here you can try the two best ways to combine them:\n"
        " • [cyan]Approach A:[/cyan] Menu-First with Real-Time Typing Filter (browse with arrows OR type to filter)\n"
        " • [cyan]Approach B:[/cyan] Input-First with Floating Arrow Dropdown (type text, arrow into completions)",
        border_style="green",
        box=box.SIMPLE
    ))

    sub_choice = questionary.select(
        "Select which hybrid pattern you want to try:",
        choices=[
            Choice("Approach A: Browse list with Arrows OR type to auto-complete filter", value="A"),
            Choice("Approach B: Input prompt with live popup dropdown you can arrow through", value="B"),
            Separator("─────────────────────────────────────────────────────"),
            Choice("« Back to Main Menu", value="back")
        ],
        style=custom_style
    ).ask()

    if sub_choice == "A":
        # Approach A: Menu is visible immediately, arrows work immediately, but typing filters choices
        console.print("\n[bold yellow]Approach A (Menu-First):[/bold yellow]")
        console.print("[dim]Use ↑/↓ arrows to scroll immediately, OR start typing (e.g. 'nvidia', 'storage', 'spine') to filter dynamically.[/dim]\n")

        switch_choices = [
            Choice("leaf-01  [NVIDIA Spectrum-3 SN3700C] - GPU Cluster Leaf (VPC-100)", value="leaf-01"),
            Choice("leaf-02  [Edgecore AS7712] - General Compute Leaf (VPC-200)", value="leaf-02"),
            Choice("leaf-03  [Celestica DX010] - High-Throughput NVMe Storage Leaf", value="leaf-03"),
            Choice("leaf-04  [Dell PowerSwitch S5248F] - Out-of-Band & Management Leaf", value="leaf-04"),
            Choice("spine-01 [NVIDIA Spectrum-4 SN5600] - 800G Non-Blocking AI Spine", value="spine-01"),
            Choice("spine-02 [Arista 7060X] - Spine Aggregation & EVPN Transit Core", value="spine-02"),
            Choice("gateway-01 [SoftGate Node] - Stateful L4-L7 Firewall & NAT Isolation", value="gateway-01"),
        ]

        picked = questionary.select(
            "Select or type switch to inspect:",
            choices=switch_choices,
            use_search_filter=True,  # Allows arrows AND typing simultaneously
            use_jk_keys=False,
            style=custom_style
        ).ask()

        if picked:
            console.print(f"\n[bold green]✔ Selected:[/bold green] [bold cyan]{picked}[/bold cyan]")

    elif sub_choice == "B":
        # Approach B: prompt_toolkit with complete_while_typing=True and arrow navigation in popup
        console.print("\n[bold yellow]Approach B (Input-First with Live Popup):[/bold yellow]")
        console.print("[dim]Start typing letters (e.g. 'vnet', '10.', 'tenant') — a menu pops up immediately below your cursor.[/dim]")
        console.print("[dim]Use [bold cyan]↑ / ↓[/bold cyan] arrow keys to move through the suggestions, and press [bold cyan]Enter[/bold cyan] to select.[/dim]\n")

        meta_dict = {
            "vnet-ai-cluster-01": "VPC-101 | EVPN VNI 1001 | RoCEv2 Lossless",
            "vnet-ai-storage-02": "VPC-101 | EVPN VNI 1002 | NVMe-oF",
            "vnet-tenant-production": "VPC-201 | EVPN VNI 2001 | Multi-Tenant Isolated",
            "vnet-tenant-staging": "VPC-201 | EVPN VNI 2002 | Multi-Tenant Isolated",
            "10.10.100.0/24 (GPU Nodes)": "Subnet isolated in VRF-AI",
            "10.20.200.0/24 (Storage Array)": "Subnet isolated in VRF-Storage",
            "172.16.1.0/24 (OOB Fabric)": "Subnet isolated in VRF-Management"
        }

        completer = WordCompleter(
            list(meta_dict.keys()),
            meta_dict=meta_dict,
            ignore_case=True,
            match_middle=True
        )

        pt_style = PtStyle.from_dict({
            "prompt": "#00d7af bold",
            "completion-menu.completion": "bg:#262626 #ffffff",
            "completion-menu.completion.current": "bg:#00d7af #000000 bold",
            "completion-menu.meta.completion": "bg:#1c1c1c #888888",
            "completion-menu.meta.completion.current": "bg:#00a888 #ffffff bold",
            "scrollbar.background": "bg:#1c1c1c",
            "scrollbar.button": "bg:#555555",
        })

        try:
            result = pt_prompt(
                [("class:prompt", "Enter or arrow-select isolation domain: ")],
                completer=completer,
                complete_while_typing=True,
                complete_style=CompleteStyle.COLUMN,
                style=pt_style
            )
            if result:
                console.print(f"\n[bold green]✔ Configured Domain:[/bold green] [bold cyan]{result}[/bold cyan]")
                if result in meta_dict:
                    console.print(f"[dim]Metadata:[/dim] {meta_dict[result]}")
        except (KeyboardInterrupt, EOFError):
            pass

    questionary.press_any_key_to_continue("\nPress any key to return to menu...").ask()


# ----------------------------------------------------------------------
# Main Showcase Menu Loop
# ----------------------------------------------------------------------
def main():
    while True:
        print_banner()

        choice = questionary.select(
            "Select a CLI menu pattern to test:",
            choices=[
                Choice("1. Arrow Navigation Menu      (Standard ↑ / ↓ list with descriptions & groups)", value="1"),
                Choice("2. Live Search & Filter      (Type to fuzzy search 20+ ports/tenants in real-time)", value="2"),
                Choice("3. Autocomplete Input         (Tab-completion with metadata popup)", value="3"),
                Choice("4. Multi-Select Checkbox      (Toggle items with Spacebar, select all with 'a')", value="4"),
                Choice("5. End-to-End Simulation      (Chained interactive switch isolation workflow)", value="5"),
                Choice("6. HYBRID: Arrows + Autocomplete (Combined arrow browsing & live typing suggestions)", value="6"),
                Separator("─────────────────────────────────────────────────────"),
                Choice("Exit", value="exit")
            ],
            style=custom_style,
            use_arrow_keys=True,
            use_jk_keys=True
        ).ask()

        if choice == "1":
            demo_arrow_select()
        elif choice == "2":
            demo_search_filter()
        elif choice == "3":
            demo_autocomplete()
        elif choice == "4":
            demo_checkbox()
        elif choice == "5":
            demo_full_workflow()
        elif choice == "6":
            demo_hybrid_arrow_autocomplete()
        elif choice in ("exit", None):
            console.print("\n[dim]Exiting Switch Isolation CLI utility. Bye![/dim]\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user.[/yellow]")
        sys.exit(0)
