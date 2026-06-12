# Architecture Overview

This document describes the design of the AI/ML reference fabric and the rationale behind the major design decisions. The intended audience is a
network engineer evaluating this design for adaptation to a production AI infrastructure deployment, or a peer reviewing the design choices.

## Design goals

The fabric is built to serve three workload categories:

- **AI/ML training traffic**  RoCEv2-encapsulated RDMA flows between GPUs, characterized by few large long-lived flows requiring lossless behavior.
- **Storage traffic**  high-throughput read/write to GPU-attached storage, also benefits from low latency and lossless transport.
- **Management/orchestration**  Kubernetes control plane, monitoring, out-of-band access, log forwarding.

The fabric is designed to deliver:

- Predictable convergence under failure (sub-second for link/node loss)
- High path diversity (ECMP across two spines, no single path bottleneck)
- Tenant isolation via VRFs and L3VNIs
- No-drop behavior for marked RoCEv2 traffic
- Operational visibility via streaming telemetry

## Physical topology

<img width="1053" height="829" alt="image" src="https://github.com/user-attachments/assets/f14d280c-81e9-4db4-9afa-a09590333891" />


A 2-spine, 4-leaf Clos topology with one GPU server per rail. Each leaf has uplinks to both spines, providing ECMP across the fabric. Each spine has
downlinks to every leaf a full mesh between spine and leaf layers (8 fabric links total).

In production, this scales to multiple rail planes per server (4+ NICs per GPU server, one to each leaf), but the protocol design is unchanged. The lab
demonstrates the design with single-rail attachment for clarity.

## Major design decisions

### Decision 1: eBGP-everywhere, not iBGP with route reflectors

The fabric uses eBGP between every adjacent pair: spines share one ASN, each leaf has a unique ASN. This is the modern AI fabric pattern adopted by hyperscalers and documented in the Cisco AI/ML CVD and Arista AI design guides.

Reasons:

1. **Deterministic convergence.** iBGP with route reflectors has known path-hunting behavior under session flap. eBGP-everywhere converges in a
   single pass.
2. **ECMP comes naturally** with `bgp bestpath as-path multipath-relax`. eBGP between different ASNs requires the relax keyword; once enabled, all paths
   across the spine layer become equal-cost.
3. **Operational simplicity.** No route reflector placement. No iBGP full-mesh problem at scale. Each leaf is a self-contained AS speaking eBGP to its
   uplinks.

### Decision 2: EVPN VXLAN with symmetric IRB, not L2 stretch

The overlay is EVPN VXLAN. Compute traffic between GPUs in the same broadcast domain is bridged at the L2VNI; routing between tenant subnets is handled at
the L3VNI within a tenant VRF.

Symmetric IRB means both source and destination leaves perform routing traffic ingresses on the L2VNI, gets routed via the L3VNI through the fabric,
then egresses on the L2VNI at the destination leaf. This is the production pattern used by Cisco NDFC and Arista CloudVision deployments.

The alternative — asymmetric IRB (routing only at the ingress leaf) requires every leaf to be configured with every tenant subnet. Symmetric IRB avoids
that, simplifying scale-out.

### Decision 3: Anycast gateway with consistent virtual MAC

Every leaf is configured with the same SVI for VLAN 100, the same IP(10.100.0.1/24), and the same virtual MAC (00:1c:73:00:00:01). When a GPU
server ARPs for its default gateway, the local leaf responds  regardless of which leaf the server is attached to.

Why this matters for AI fabrics specifically: AI workloads often have multiple NICs per server, one per rail, each potentially on a different leaf. Without
anycast gateway, traffic from each NIC traverses to a specific gateway leaf, adding hops. With anycast gateway, every leaf is "the gateway" minimum-latency
egress for every flow.

### Decision 4: BFD timers at 250ms

BGP timers alone (3-second hello, 9-second hold) provide ~9-second convergence after a failure. For AI workloads, 9 seconds of stalled collective
communication can break a training job.

BFD with 250ms timers (interval 250, min-rx 250, multiplier 3) detects peer death in ~750ms and triggers BGP withdrawal immediately. Combined with
multipath ECMP, sub-second convergence is achievable on real hardware. On cEOS-lab, BFD negotiates correctly but true convergence timing requires
hardware to validate.

### Decision 5: MTU 9214 on fabric, 9000 on servers

The fabric carries VXLAN-encapsulated traffic. The ~50-byte VXLAN header(outer IP + outer UDP + VXLAN + inner Ethernet) plus headroom must be
accommodated. MTU 9214 is Arista's maximum jumbo and gives margin for encapsulation overhead.

Servers are configured at MTU 9000 to avoid sending packets that would require fragmentation once encapsulated. The 214-byte gap absorbs all VXLAN encap
variations without fragmentation.

### Decision 6: RoCEv2 QoS markings

Traffic class assignment follows the Cisco AI/ML CVD and NVIDIA Spectrum-X conventions:

| Traffic        | DSCP     | CoS | Behavior              |
|----------------|----------|-----|-----------------------|
| RoCEv2 data    | 24 (CS3) | 3   | No-drop, ECN-marked   |
| CNP feedback   | 48 (CS6) | 6   | Strict priority       |
| Best effort    | 0        | 0   | Default, drop-eligible|

This marking is consistent across vendors. A GPU server configured for RoCEv2 on NVIDIA ConnectX NICs marks data traffic with DSCP 24 by default; switches
preserve and act on the marking. See `qos-design.md` for thresholds.

### Decision 7: Automation-first operational model

The fabric is configured manually first (to learn the protocols), then re-implemented as idempotent Ansible roles. Subsequent fabric changes are made
by modifying inventory data, not switches.

This is the production engineering pattern: learn manually, then automate. A large fabric cannot be reliably maintained by hand. The pyATS validation
framework provides automated assertions after any change — if a playbook makes the fabric unhealthy, the test suite catches it.

## What's deliberately out of scope

This lab uses Arista cEOS in containerlab. Configuration design and control plane behavior are validated. The following AI-specific behaviors require
silicon and are NOT validated in this environment:

- PFC pause frame generation and consumption
- ECN marking at queue depth thresholds
- DLB flowlet detection and per-flowlet rebalancing
- DCQCN response loop on host NICs
- Real congestion behavior under sustained AI workload

The QoS and DLB designs (`qos-design.md`, `dlb-design.md`) are documented as deployable specifications for real Arista 7280R3/7388X hardware or equivalent
Cisco Nexus 9300-FX/GX/H platforms, with threshold values cited from the Cisco AI/ML CVD and Meta's SIGCOMM 2024 paper.

## Hardware deployment targets

The design is portable to the following platforms with documented syntax equivalents (see `cisco-vs-arista-syntax.md`):

| Vendor | Platform                  | Suitable role                          |
|--------|---------------------------|----------------------------------------|
| Arista | 7280R3 series             | Leaf or spine, full RoCE               |
| Arista | 7388X series              | AI-optimized leaf                      |
| Arista | 7800R series              | Modular spine                          |
| Cisco  | Nexus 9300-FX2/FX3        | Leaf, full RoCE                        |
| Cisco  | Nexus 9300-GX/GX2         | AI-optimized leaf (400G/800G)          |
| Cisco  | Nexus 9500-R series       | Modular spine                          |
| Cisco  | Nexus 9300-H (Silicon One)| AI factory-grade leaf                  |
