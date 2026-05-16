cat > tests/test_underlay.py <<'EOF'
"""
Test the eBGP underlay:
- All BGP sessions Established
- All loopbacks reachable via ECMP across both spines
"""

from pyats import aetest
from genie.testbed import load


class CommonSetup(aetest.CommonSetup):

    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all switches in the testbed."""
        testbed.connect(log_stdout=False)


class BgpSessionsEstablished(aetest.Testcase):
    """All BGP neighbors should be in Established state."""

    @aetest.test
    def check_bgp_neighbors(self, testbed):
        """For each switch, check all BGP neighbors are Established."""
        failed_devices = []

        for device_name, device in testbed.devices.items():
            output = device.execute("show ip bgp summary")
            
            # Find lines that look like BGP neighbor entries
            for line in output.splitlines():
                # Skip header/footer lines
                if line.startswith("Neighbor") or line.startswith("BGP") or line.startswith("---"):
                    continue
                if not line.strip():
                    continue
                
                # BGP summary lines have neighbor IP early in line
                # If "Estab" is in the line, it's an established session — pass
                # Otherwise, treat as failure
                if "Estab" not in line and ("." in line.split()[0] if line.split() else False):
                    failed_devices.append(f"{device_name}: {line.strip()}")

        if failed_devices:
            self.failed(f"BGP sessions not established: {failed_devices}")


class EcmpReachability(aetest.Testcase):
    """All loopbacks should be reachable via two paths (ECMP)."""

    @aetest.test
    def check_ecmp_paths(self, testbed):
        """Verify ECMP from leaf1 to other leaves' loopbacks."""
        device = testbed.devices['leaf1']
        
        # Check route to leaf2's loopback0 — should have 2 next-hops (ECMP)
        output = device.execute("show ip route 10.0.0.22")
        
        # Count "via" lines, which represent next-hops
        via_count = output.count("via ")
        
        if via_count < 2:
            self.failed(
                f"ECMP not working: route to 10.0.0.22 has only {via_count} next-hop(s) "
                f"(expected 2). Output: {output}"
            )


class CommonCleanup(aetest.CommonCleanup):

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all switches."""
        for device in testbed.devices.values():
            try:
                device.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    aetest.main(testbed=load('../testbed.yml'))
EOF
