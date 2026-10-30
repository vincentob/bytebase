"""Configuration for the isolated permission fixtures and role import tools."""

import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
POC = ROOT / "poc"
STATE = POC / ".state"
CONFIG = yaml.safe_load((POC / "config.yaml").read_text())
API_URL = CONFIG["api_url"]
COMPOSE = ["docker", "compose", "-f", str(POC / "compose.yaml")]


def log(message, level="INFO"):
    colors = {"INFO": "32", "WARN": "33", "ERROR": "31"}
    prefix = f"[{level}]"
    if sys.stderr.isatty() and not os.getenv("NO_COLOR"):
        prefix = f"\033[{colors[level]}m{prefix}\033[0m"
    print(f"{prefix} {message}", file=sys.stderr, flush=True)


def run(args, cwd=ROOT, env=None, capture=False, input=None):
    return subprocess.run(
        [str(arg) for arg in args], cwd=cwd,
        env={**os.environ, **(env or {})}, check=True,
        capture_output=capture, text=True, input=input,
    )


def state_directory():
    STATE.mkdir(exist_ok=True)
    STATE.chmod(0o700)


def role_definitions():
    roles = yaml.safe_load((POC / "roles.yaml").read_text())["roles"]
    for name, role in roles.items():
        if not name.isalnum() or not role.get("permissions"):
            raise ValueError("Role IDs and permission sets must be non-empty")
        permissions = role["permissions"]
        if len(permissions) != len(set(permissions)) or not all(p.startswith("bb.") for p in permissions):
            raise ValueError(f"Invalid permission set for {name}")
    return roles
