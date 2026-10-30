"""Ensure fixture seeding cannot target the daily application data directory."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import manage


def context(mount_type="volume"):
    return [
        SimpleNamespace(stdout="test-container\n"),
        SimpleNamespace(stdout="true\n"),
        SimpleNamespace(stdout=json.dumps([{
            "Destination": "/var/opt/bytebase", "Type": mount_type,
            "Name": "bytebase-permission-tests_metadata",
        }])),
        SimpleNamespace(stdout=json.dumps({"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "17880"}]})),
    ]


class FixtureContextTest(unittest.TestCase):
    def test_accepts_the_owned_volume_and_loopback_port(self):
        with patch.object(manage, "run", side_effect=context()):
            manage.require_fixture_stack()

    def test_rejects_a_bind_mount_even_on_a_labeled_container(self):
        with patch.object(manage, "run", side_effect=context("bind")):
            with self.assertRaisesRegex(RuntimeError, "dedicated metadata volume"):
                manage.require_fixture_stack()

    def test_rejects_a_remote_api_even_when_the_fixture_container_exists(self):
        with patch.object(manage, "run", side_effect=context()), patch.object(manage, "API_URL", "https://bytebase.example.com"):
            with self.assertRaisesRegex(RuntimeError, "loopback port"):
                manage.require_fixture_stack()

    def test_rejects_the_daily_application_port(self):
        with patch.object(manage, "run", side_effect=context()), patch.object(manage, "API_URL", "http://127.0.0.1:8088"):
            with self.assertRaisesRegex(RuntimeError, "loopback port"):
                manage.require_fixture_stack()


if __name__ == "__main__":
    unittest.main()
