# Dynamic Load Balancing and ECMP Design

## Purpose

Standard 5-tuple ECMP fails for AI/ML traffic patterns. AI workloads produce a small number of huge, long-lived flows (typically 4-16 flows per GPU pair). With 5-tuple hashing, these flows collide on the same paths, leaving other 
fabric paths underutilized while collision links saturate. 

This document specifies the load-balancing enhancements to address this for the AI/ML reference fabric.

## The Elephant Flow Problem

Traditional ECMP assumes many small flows. Statistical distribution across paths is approximately uniform, and per-flow consistency (no reordering) is preserved.

AI traffic violates both assumptions:

1 **Few flows:** A 64-GPU all-reduce produces 64 long lived flows total
2 **Same characteristics:** All RoCE flows hash similarly (same protocol, similar port ranges)
3 **Long duration:** Flows persist for the entire training step (seconds to minutes)
4 **Bandwidth-heavy:** Each flow may consume 80-100% of NIC capacity

Result: 5-tuple hashing puts multiple elephant flows on the same fabric path, causing congestion on that path while other paths sit idle. JCT (Job Completion Time) suffers because the slowest flow stalls the collective.

## Three-Layer Solution

The design addresses elephant flows at three layers:

### Layer 1: VXLAN Inner-Header Hashing

Without this, every VXLAN-encapsulated flow between two VTEPs has the same outer 5-tuple guaranteeing identical hashing for all overlay traffic. This is the silent killer of AI fabric performance.

**Configuration concept:** Enable inner-header parsing for ECMP hash computation, ensuring the underlay hashes on the inner flow's 5-tuple, not the outer VXLAN encapsulation.

### Layer 2: Dynamic Load Balancing (DLB)

DLB monitors per-path utilization in hardware and adapts flow placement based on real-time congestion. Two operating modes:

1 **Flowlet mode:** Detects gaps (64 μs) within a flow and rebalances at flowlet boundaries. Safe no packet reordering during bursts.
2 **Per-packet mode:** Sprays packets across all paths. Maximum balance but requires NIC side reordering tolerance.

For RoCE aware fabrics, **flowlet mode is the standard**  RoCE NICs don't tolerate reordering well, but flowlet boundaries align with natural traffic 
gaps.

### Layer 3: Resilient Hashing

When a fabric link fails, traditional ECMP rehashes ALL flows across remaining paths disrupting flows that didn't traverse the failed link. Resilient hashing only redistributes flows from the failed path, leaving healthy flows 
undisturbed.

This dramatically reduces collateral disruption during fabric failures.

## Configuration (Arista hardware)

### Hash polynomial diversity

Different leaves use different hash polynomials to avoid systemic collisions when fabric topology has exact symmetry.

load-balance policies
load-balance fabric profile AI-FABRIC
seed 0x{leaf-specific-value}
fields ip protocol src-ip dst-ip src-port dst-port
vxlan inner-header
!

### DLB enablement
load-balance policies
load-balance fabric profile AI-FABRIC
mode dynamic
dynamic mode flowlet inactivity-timer 64
port-mode dlb
!

### Per-interface application
interface Ethernet49
load-balance fabric profile AI-FABRIC
!
interface Ethernet50
load-balance fabric profile AI-FABRIC
!

### Resilient hashing
ip hardware fec mode resilient

## Validation Boundaries

This design **cannot be validated** in containerlab + cEOS-lab. Specific gaps:

**Configuration commands not accepted by cEOS:**
1 "load-balance fabric profile" silicon-specific feature
2 "mode dynamic" / "dynamic mode flowlet" requires hardware path utilization tracking
3 "vxlan inner-header" ECMP hashing requires hardware parser
4 "ip hardware fec mode resilient" silicon specific

**What can be validated in containerlab:**
1 Standard ECMP across both spines (validated in Day 6 "show ip route" shows two next-hops for any remote loopback)
2 VXLAN encapsulation/decapsulation (validated in Day 7)

**What requires hardware:**
1 DLB flowlet detection and path rebalancing
2 VXLAN inner-header hash computation
3 Resilient hashing behavior under link failure
4 Real elephant flow distribution under AI workloads

## Hardware Deployment Targets

| Platform | DLB Support | Inner-header hashing | Resilient hashing |
|----------|-------------|----------------------|-------------------|
| Arista 7280R3 | Yes | Yes | Yes |
| Arista 7388X (Spectrum-X) | Yes | Yes | Yes |
| Arista 7800R series | Yes | Yes | Yes |
| Cisco Nexus 9300-GX | Yes (DLB) | Yes | Yes |
| Cisco Nexus 9300-FX3 | Yes (CONGA) | Yes | Yes |

Cisco syntax equivalents documented in `docs/cisco-vs-arista-syntax.md`.

## Phase 2 Validation Plan

Real validation requires:

1 Hardware switches with DLB silicon (Arista 7280R3+ or Cisco 9300-GX+)
2 Multi-host AI workload generating elephant flows
3 Per-port utilization telemetry under load

Without hardware access, Phase 2 GPU testing on Lambda Labs validates end-to-end performance but cannot isolate DLB-specific behavior since the provider's switching layer is opaque.

## References

-1 Cisco Data Center Networking Blueprint for AI/ML Applications
2 Cisco AI/ML CVD section on traffic distribution
3 Meta Distributing AI Training Traffic Across Networks (SIGCOMM 2024)
4 Arista EOS Load Balancing Configuration Guide
5 "On the Impact of Packet Spraying in Data Center Networks"  Dixit et al.
