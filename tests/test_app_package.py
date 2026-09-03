import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppPackageContractTest(unittest.TestCase):
    def test_app_declares_the_minimum_gateway_privileges_and_watchdog(self):
        config = (ROOT / "app" / "config.yaml").read_text()

        self.assertIn("host_network: true", config)
        self.assertIn("  - NET_ADMIN", config)
        self.assertNotIn("full_access: true", config)
        self.assertIn("watchdog: http://[HOST]:[PORT:45987]/health", config)
        self.assertIn("boot: auto", config)
        self.assertIn("startup: system", config)
        self.assertIn("ingress: true", config)

    def test_default_options_are_fail_closed_and_match_the_fixed_topology(self):
        config = (ROOT / "app" / "config.yaml").read_text()

        for literal in (
            "lan_interface: enp4s0",
            "wan_interface: enp2s0",
            "source_cidr: 192.168.50.0/24",
            "heartbeat_interval: 15",
            "lease_timeout: 45",
        ):
            self.assertIn(literal, config)


if __name__ == "__main__":
    unittest.main()
