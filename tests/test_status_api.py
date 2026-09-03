import unittest

from gateway.app import status_document
from gateway.service import GatewayStatus


class StatusApiContractTest(unittest.TestCase):
    def test_health_document_exposes_the_operational_contract(self):
        status = GatewayStatus(
            state="enabled",
            expires_at=1045.0,
            lan_interface="enp4s0",
            wan_interface="enp2s0",
            source_cidr="192.168.50.0/24",
            rules_checksum="abc123",
        )

        document = status_document(status, packet_counters={"outbound": 7, "blocked": 2})

        self.assertEqual(
            {
                "state": "enabled",
                "enabled": True,
                "expires_at": 1045.0,
                "lan_interface": "enp4s0",
                "wan_interface": "enp2s0",
                "source_cidr": "192.168.50.0/24",
                "rules_checksum": "abc123",
                "packet_counters": {"outbound": 7, "blocked": 2},
            },
            document,
        )


if __name__ == "__main__":
    unittest.main()
