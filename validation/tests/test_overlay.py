cat > tests/test_overlay.py <<'EOF'
"""
Test the EVPN VXLAN overlay:
- EVPN BGP sessions Established
- All leaves see 3 remote VTEPs
- End-to-end ping from gpu-srv1 to gpu-srv4 works
"""

from pyats import aetest
from genie.testbed import load
import subprocess


class CommonSetup(aetest.CommonSetup):

    @aetest.subsection
    def connect_to_devices(self, testbed):
        testbed.connect(log_stdout=False)


class EvpnSessionsEstablished(aetest.Testcase):
    """All leaves should have EVPN sessions to both spines, Established."""

    @aetest.test
    def check_evpn_neighbors(self, testbed):
        failed = []
        
        for device_name, device in testbed.devices.items():
            # Only check leaves and spines (no servers in pyATS testbed)
            output = device.execute("show bgp evpn summary")
            
            # Count Estab entries
            estab_count = output.count("Estab")
            
            # Spines should have 4 EVPN neighbors (one per leaf)
            # Leaves should have 2 EVPN neighbors (one per spine)
            expected_count = 4 if "spine" in device_name else 2
            
            if estab_count < expected_count:
                failed.append(
                    f"{device_name}: {estab_count} Established (expected {expected_count})"
                )
        
        if failed:
            self.failed(f"EVPN session count issues: {failed}")


class VtepDiscovery(aetest.Testcase):
    """All leaves should see 3 remote VTEPs."""

    @aetest.test
    def check_remote_vteps(self, testbed):
        failed = []
        
        for device_name, device in testbed.devices.items():
            if "leaf" not in device_name:
                continue
            
            output = device.execute("show vxlan vtep")
            
            # Count VTEP IP addresses (start with 10.0.0.12)
            vtep_count = sum(1 for line in output.splitlines() if line.startswith("10.0.0.12"))
            
            if vtep_count < 3:
                failed.append(f"{device_name}: {vtep_count} remote VTEPs (expected 3)")
        
        if failed:
            self.failed(f"VTEP discovery issues: {failed}")


class EndToEndConnectivity(aetest.Testcase):
    """gpu-srv1 should ping gpu-srv4 across the fabric."""

    @aetest.test
    def ping_gpu_srv1_to_gpu_srv4(self, testbed):
        # Run ping from automation-host via docker exec
        result = subprocess.run(
            ["docker", "exec", "clab-ai-fabric-gpu-srv1", "ping", "-c", "3", "-W", "2", "10.100.0.14"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            self.failed(f"Ping failed:\n{result.stdout}\n{result.stderr}")
        
        # Check for actual successful replies
        if "0% packet loss" not in result.stdout:
            self.failed(f"Packet loss detected:\n{result.stdout}")


class CommonCleanup(aetest.CommonCleanup):

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        for device in testbed.devices.values():
            try:
                device.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    aetest.main(testbed=load('../testbed.yml'))
EOF
