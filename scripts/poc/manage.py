"""Manage isolated permission tests or synchronize role definitions to an instance."""

import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

import yaml

from settings import API_URL, COMPOSE, POC, STATE, log, role_definitions, run, state_directory


def require_fixture_stack():
    container = run(COMPOSE + ["ps", "--quiet", "bytebase"], capture=True).stdout.strip()
    if not container:
        raise RuntimeError("Start the isolated fixture stack with make poc:up first")
    label = run([
        "docker", "inspect", "--format",
        '{{ index .Config.Labels "dev.bytebase.permission-tests" }}', container,
    ], capture=True).stdout.strip()
    if label != "true":
        raise RuntimeError("The container is not owned by the permission test stack")
    mounts = json.loads(run(["docker", "inspect", "--format", "{{json .Mounts}}", container], capture=True).stdout)
    if not any(
        mount.get("Destination") == "/var/opt/bytebase"
        and mount.get("Type") == "volume"
        and mount.get("Name") == "bytebase-permission-tests_metadata"
        for mount in mounts
    ):
        raise RuntimeError("Permission fixtures require their dedicated metadata volume")
    ports = json.loads(run(["docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", container], capture=True).stdout)
    url = urlsplit(API_URL)
    if (
        url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost")
        or url.path not in ("", "/") or url.query or url.fragment or url.username
        or not any(p.get("HostIp") == "127.0.0.1" and p.get("HostPort") == str(url.port) for p in ports.get("8080/tcp", []))
    ):
        raise RuntimeError("The fixture API must use the isolated container's loopback port")


def seed():
    require_fixture_stack()
    state_directory()
    path = STATE / "database.yaml"
    if not path.exists():
        with open(path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as output:
            yaml.safe_dump({"password": secrets.token_urlsafe(24)}, output)
    password = yaml.safe_load(path.read_text())["password"]
    sql = (POC / "fixtures/init.sql").read_text()
    run(COMPOSE + [
        "exec", "-T", "--env", "BYTEBASE_POC_DB_PASSWORD", "bytebase",
        "psql", "-h", "/tmp", "-p", "8082", "-U", "bb", "-d", "postgres",
    ], env={"BYTEBASE_POC_DB_PASSWORD": password}, capture=True, input=sql)
    from api import seed as seed_api
    seed_api()


def sync_roles(url):
    from api import Client, sync_roles as sync
    client = Client(os.getenv("BYTEBASE_ADMIN_TOKEN"), base_url=url)
    if not client.token:
        email = input("Admin email: ").strip()
        response = client.request("POST", "/v1/auth/login", {
            "email": email, "password": getpass.getpass("Admin password: "), "web": False,
        })
        if not response.get("token"):
            raise RuntimeError("A full admin token is required; set BYTEBASE_ADMIN_TOKEN for MFA accounts")
        client.token = response["token"]
    sync(client)
    log("Custom role definitions synchronized; user and project bindings were preserved")


def browser_test():
    require_fixture_stack()
    run(["pnpm", "--dir", "frontend", "exec", "playwright", "test", "--config", str(POC / "playwright.config.mjs")])


def go_test():
    architecture = run(["docker", "info", "--format", "{{.Architecture}}"], capture=True).stdout.strip()
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(architecture)
    if not arch:
        raise RuntimeError("Unsupported Docker architecture")
    env = {"GOOS": "linux", "GOARCH": arch, "CGO_ENABLED": "0"}
    with tempfile.TemporaryDirectory(prefix="bytebase-permission-go-", dir="/tmp") as directory:
        binary = Path(directory) / "server.test"
        run(["go", "test", "-c", "-tags", "permission_poc", "-o", binary, "./backend/server"], env=env)
        run(["docker", "run", "--rm", "--network", "none", "-v", f"{binary}:/server.test:ro", "debian:bookworm-slim", "/server.test", "-test.run", "^(TestPermissionPoCProfile|TestPermissionPoCListenAddress|TestPersonalPermissionPolicy)$", "-test.v"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seed", "api-test", "browser-test", "test", "roles", "validate", "go-test"])
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Target URL for roles only")
    args = parser.parse_args()
    if args.command == "roles":
        sync_roles(args.url)
    elif args.command == "validate":
        role_definitions()
        log("Role definitions are valid")
    elif args.command == "seed":
        seed()
    elif args.command == "browser-test":
        browser_test()
    elif args.command == "go-test":
        go_test()
    else:
        seed()
        from api import test
        test()
        if args.command == "test":
            browser_test()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, subprocess.CalledProcessError, OSError) as error:
        log(str(error), "ERROR")
        sys.exit(1)
