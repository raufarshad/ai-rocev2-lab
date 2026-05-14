# RoCEv2 QoS Design

## Purpose

This document specifies the QoS design for the AI/ML reference fabric to support RoCEv2 traffic with lossless Ethernet semantics. Configurations are validated 
against Arista hardware platform documentation (7280R3 / 7388X class) but cannot be executed in cEOS-lab see "Validation Boundaries" below.

## Scope

The QoS design supports two RoCE traffic categories:

**RoCEv2 data:** AI/ML training collective communication (NCCL, MPI). Bulk traffic that must remain lossless.
  
**Congestion Notification Packets (CNPs):** ECN feedback from receiving NICs back to senders. Small packets that must be delivered with high priority.

## Marking Strategy

| Traffic | DSCP | CoS | Traffic Class | Behavior |
|---------|------|-----|---------------|----------|
| RoCEv2 data | 24 (CS3) | 3 | 3 | No-drop (PFC), ECN marking |
| CNP feedback | 48 (CS6) | 6 | 5 | Strict priority, no marking |
| Best effort | 0 | 0 | 0 | Drop-eligible, default |

These markings follow the convention adopted by Cisco's AI/ML CVD, NVIDIA's Spectrum-X documentation, and Meta's RDMA deployment.

## ECN Thresholds

WRED with ECN marking is configured on the no-drop traffic class with these thresholds, sourced from the Cisco AI/ML CVD:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min threshold | 150 KB | Allows ~100 small packets to queue without ECN |
| Max threshold | 3000 KB | Aggressive marking before PFC engagement |
| Max drop probability | 7% | Aligns with Meta SIGCOMM 2024 published value |
| PFC pause threshold | ~80% buffer | Triggers only if ECN response insufficient |
| PFC resume threshold | ~50% buffer | Hysteresis prevents pause flapping |
| PFC watchdog | 200 ms | Detects stuck PFC storms; recovers in <1s |
| MTU | 9214 | Maximum Arista jumbo MTU |

## Configuration (Arista hardware)

### Classification (input policy)

Applied to all fabric and server-facing interfaces.

class-map type qos match-any AI-DATA-DSCP
match ip dscp 24
!
class-map type qos match-any CNP-DSCP
match ip dscp 48
!
policy-map type quality-of-service AI-FABRIC-QOS
class AI-DATA-DSCP
set traffic-class 3
class CNP-DSCP
set traffic-class 5
class class-default
set traffic-class 0
!

### Egress queueing (output policy)

WRED with ECN marking on TC 3, strict priority on TC 5.

policy-map type tx-queue AI-EGRESS-QUEUE
class tx-queue 3
bandwidth percent 50
random-detect ecn minimum-threshold 150 kbytes maximum-threshold 3000 kbytes max-mark-probability 7
class tx-queue 5
priority strict
bandwidth percent 5
!

### Per-interface PFC

Applied to all fabric uplinks and server-facing ports.

interface Ethernet1
service-policy type qos input AI-FABRIC-QOS
service-policy type tx-queue output AI-EGRESS-QUEUE
priority-flow-control on
priority-flow-control priority 3 no-drop
!

### Global PFC watchdog

priority-flow-control pause watchdog default action drop timer 200 milliseconds polling-interval 50 milliseconds

## Validation Boundaries

This design **cannot be validated** in containerlab + cEOS-lab. Specific gaps:

**Configuration commands not accepted by cEOS:**
1 "match ip dscp" requires hardware ACL TCAM
2 "priority-flow-control" interface and global commands requires per-priority pause frame silicon
3 "random-detect ecn" with kbyte thresholds requires hardware queue depth tracking
4 "policy-map type tx-queue" requires hardware traffic manager

These features are silicon-dependent and not present in the cEOS software forwarding path.

**What can be validated in containerlab:**
1 Classification and marking concepts via packet inspection (tcpdump, DSCP visible in IP header)
2 BGP, EVPN, VXLAN forwarding with QoS markings preserved end-to-end
3 Configuration syntax against Arista platform documentation

**What requires hardware:**
1 Real PFC pause frame generation under congestion
2 ECN marking at threshold crossings
3 DCQCN response loop on host NICs
4 DLB and resilient hashing under load

## Hardware Deployment Targets

This design is validated against the following Arista platforms:

1 **Arista 7280R3 series** Cloud Networking, full RoCE feature support
2 **Arista 7388X series** AI/ML data center, Spectrum-X-equivalent feature set
3 **Arista 7800R series** Modular, full RoCE feature support

Equivalent Cisco platforms with documented syntax mapping:

1 **Cisco Nexus 9300-FX2/FX3 series** equivalent of Arista 7280R3
2 **Cisco Nexus 9300-GX series** high-radix AI fabric leaf
3 **Cisco Nexus 9500-R/R2 series** modular spine

Cisco syntax equivalents are documented separately in "docs/cisco-vs-arista-syntax.md".

## Phase 2 Validation Plan

Real validation of this QoS design requires hardware. The Phase 2 cloud GPU validation track will:

1. Rent two GPU instances (H100/A100) on Lambda Labs with RoCE-capable NICs
2. Configure host side RoCE per `docs/host-roce-config.md` (to be authored)
3. Run NCCL all-reduce benchmarks across both nodes
4. Capture: bandwidth-by-message-size, latency distribution, ECN-marked packet counts (where observable from the host side)
5. Document: real-world RoCE/RDMA performance numbers, congestion behavior under load

This will be tracked separately as a Phase 2 deliverable.

## References

1 Cisco Data Center Networking Blueprint for AI/ML Applications
2 Cisco Validated Design for AI/ML Networking
3 Meta RDMA over Ethernet for Distributed AI Training (SIGCOMM 2024)
4 NVIDIA Spectrum-X Architecture
5 Arista EOS QoS Configuration Guide
