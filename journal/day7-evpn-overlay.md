# Day 7 — EVPN VXLAN Overlay

**Status:** ✅ Complete and validated end-to-end

## What was built

eBGP-EVPN overlay running on top of the Day 6 underlay:
- 2 EVPN BGP sessions per leaf (one to each spine)
- Spines re-advertise EVPN routes between leaves (transit-only, no VTEPs)
- VLAN 100 L2VNI 30100 mapping
- VRF "ai-training" with L3VNI 50000 (symmetric IRB)
- Anycast gateway with virtual MAC "00:1c:73:00:00:01" (identical on all leaves)
- VXLAN encapsulation/decapsulation at leaf VTEPs (Loopback1)

## Validation

End-to-end ping verified across the fabric:
- gpu-srv1 (10.100.0.11, attached to leaf1) → gpu-srv4 (10.100.0.14, attached to leaf4)
- Traffic encapsulates at leaf1's VTEP, routes via spine, decapsulates at leaf4's VTEP
- All 4 leaves see 3 remote VTEPs in `show vxlan vtep`
- MAC table shows local + remote MAC learning via Vx1 (VXLAN interface)

## Gotcha worth documenting

Cross-leaf VXLAN forwarding required explicit route-target configuration

router bgp <ASN>
vlan 100
route-target both 30100:30100

The "auto" route-target on leaves alone wasn't sufficient for the L2VNI in this configuration. Once explicit route-target was added, type-2 MAC/IP routes propagated immediately.

This is exactly the kind of detail not found in the Cisco CVD or vendor documentation it surfaces only when actually building the fabric.

## What's next

**Day 8 (RoCE QoS):** Documentation-only on cEOS-lab. Configuration commands for PFC, ECN, and per-queue WRED are silicon-dependent and not accepted by cEOS. 
The QoS design will be captured in `docs/qos-design.md` with threshold values cited from the Cisco AI/ML CVD and Meta SIGCOMM paper, deployable to real Arista 7280R3/7388X hardware.

**Phase 2 (real validation):** Cloud GPU rental on Lambda Labs to run nccl-tests on H100 instances with real RoCE NICs. This is where actual congestion behavior and DCQCN can be validated.
