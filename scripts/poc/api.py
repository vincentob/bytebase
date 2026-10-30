"""Seed and verify the disposable Bytebase instance on the loopback interface."""

from datetime import datetime, timedelta, timezone
import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request

import yaml

from settings import API_URL, CONFIG, POC, STATE, log, role_definitions, state_directory


class Client:
    def __init__(self, token=None, base_url=API_URL):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, body=None, statuses=(200,)):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(self.base_url + path, method=method, headers=headers,
                                         data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, content = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, content = error.code, error.read()
        payload = json.loads(content) if content else {}
        self.last_status = status
        if status not in statuses:
            raise RuntimeError(f"{method} {path}: expected {statuses}, received HTTP {status}: {payload.get('message', payload.get('error', ''))}")
        return payload


def credentials():
    state_directory()
    path = STATE / "accounts.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text())
    data = {role: {"email": CONFIG["accounts"][role], "password": secrets.token_urlsafe(24)}
            for role in ["owner", "dev", "leader"]}
    with open(path, "x", opener=lambda p, flags: os.open(p, flags, 0o600)) as output:
        yaml.safe_dump(data, output)
    return data


def login(role):
    response = Client().request("POST", "/v1/auth/login", {**credentials()[role], "web": False})
    return Client(response["token"])


def bindings_for(project):
    accounts = credentials()
    bindings = [
        {"role": "roles/projectOwner", "members": ["user:" + accounts["owner"]["email"]]},
        {"role": "roles/pocsubmitter", "members": ["user:" + accounts["leader"]["email"]]},
    ]
    if project == "poc-sandbox":
        bindings.append({"role": "roles/pocdeveloper", "members": ["user:" + accounts["dev"]["email"]]})
    return bindings


def set_project_policy(owner, project, bindings):
    return owner.request("POST", f"/v1/projects/{project}:setIamPolicy", {"policy": {"bindings": bindings}})


def sync_roles(owner):
    for name, role in role_definitions().items():
        owner.request(
            "PATCH", f"/v1/roles/{name}?allowMissing=true&updateMask=title,description,permissions",
            {"name": "roles/" + name, "description": role.get("description", ""), **role},
        )


def wait_database_metadata(owner, project, database, table="permission_fixture", timeout=40):
    resource = f"/v1/projects/{project}/instances/{project}/databases/{database}"
    owner.request("POST", resource + ":sync", {})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        metadata = owner.request("GET", resource + "/metadata", statuses=(200, 404))
        if any(
            schema.get("name") == "public" and any(t.get("name") == table for t in schema.get("tables", []))
            for schema in metadata.get("schemas", [])
        ):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Schema metadata for {project}/{database}/{table} was not synced")


def seed():
    accounts = credentials()
    first = Client().request("POST", "/v1/auth/signup", {
        **accounts["owner"], "title": "PoC Owner",
    }, (200, 409))
    owner = Client(first["token"]) if "token" in first else login("owner")
    for role in ["dev", "leader"]:
        owner.request("POST", "/v1/users", {**accounts[role], "title": "PoC " + role.title()}, (200, 409))
    sync_roles(owner)
    workspace = owner.request("GET", "/v1/users/me")["workspace"]
    owner.request("POST", "/v1/" + workspace + ":setIamPolicy", {"policy": {"bindings": [
        {"role": "roles/workspaceAdmin", "members": ["user:" + accounts["owner"]["email"]]},
        {"role": "roles/pocbase", "members": ["user:" + accounts[r]["email"] for r in ["dev", "leader"]]},
    ]}})
    for project, database in [("poc-sandbox", "sandbox_poc"), ("poc-prod", "prod_poc")]:
        owner.request("POST", "/v1/projects?projectId=" + project,
                      {"title": "PoC Sandbox" if project == "poc-sandbox" else "PoC Production"}, (200, 409))
        set_project_policy(owner, project, bindings_for(project))
        owner.request("POST", f"/v1/projects/{project}/instances?instanceId={project}", {
            "title": "PoC " + project, "engine": "POSTGRES", "syncDatabases": {"databases": [database]},
            "dataSources": [{"id": "admin", "type": "ADMIN", "host": "/tmp", "port": "8082",
                             "username": "poc", "password": yaml.safe_load((STATE / "database.yaml").read_text())["password"], "database": database}],
        }, (200, 409))
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            found = owner.request("GET", f"/v1/projects/{project}/databases").get("databases", [])
            if any(d["name"].endswith("/databases/" + database) for d in found):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Test database metadata was not synced")
        wait_database_metadata(owner, project, database)
    log("Local owner/dev/leader users, custom roles and fixture databases are ready; credentials are in poc/.state/accounts.yaml")


def query(client, project, database, sql, statuses=(200,)):
    path = f"/v1/projects/{project}/instances/{project}/databases/{database}:query"
    result = client.request("POST", path, {"statement": sql, "limit": 20}, (200, 403) if statuses == (403,) else statuses)
    if statuses == (403,):
        denied = client.last_status == 403 or (
            bool(result.get("results")) and all(item.get("permissionDenied") and not item.get("rows") for item in result["results"])
        )
        if not denied:
            raise RuntimeError("Query unexpectedly passed its authorization check")
        return result
    if statuses == (200,) and (not result.get("results") or any(item.get("error") for item in result["results"])):
        raise RuntimeError("Fixture SQL execution failed: " + str([item.get("error") for item in result["results"]]))
    return result


def submit_change(client, project, database):
    title = "Permission PoC " + secrets.token_hex(6)
    sheet = client.request("POST", f"/v1/projects/{project}/sheets", {
        "content": base64.b64encode(b"ALTER TABLE public.permission_fixture ADD COLUMN poc_review integer").decode(),
    })
    plan = client.request("POST", f"/v1/projects/{project}/plans", {
        "title": title,
        "specs": [{"id": "poc-change", "changeDatabaseConfig": {
            "targets": [f"projects/{project}/instances/{project}/databases/{database}"],
            "sheet": sheet["name"],
        }}],
    })
    issue = client.request("POST", f"/v1/projects/{project}/issues", {
        "title": title, "type": "DATABASE_CHANGE", "plan": plan["name"],
    })
    return plan, issue


def test():
    owner, dev, leader = login("owner"), login("dev"), login("leader")
    results = []
    workspace = owner.request("GET", "/v1/users/me")["workspace"]
    policies = ["/v1/" + workspace + ":getIamPolicy"] + [
        f"/v1/projects/{project}:getIamPolicy" for project in ["poc-sandbox", "poc-prod"]
    ]
    before = [owner.request("GET", path) for path in policies]
    sync_roles(owner)
    if before != [owner.request("GET", path) for path in policies]:
        raise RuntimeError("Role synchronization changed workspace or project IAM")
    results.append("owner: role synchronization preserves workspace and project IAM")
    Client().request("GET", "/poc/self-permissions", statuses=(401,))
    for role, client in [("dev", dev), ("leader", leader)]:
        for path in ["/v1/roles", "/v1/users"]:
            client.request("GET", path, statuses=(403,))
        workspace = client.request("GET", "/v1/users/me")["workspace"]
        client.request("GET", "/v1/" + workspace + ":getIamPolicy", statuses=(403,))
        snapshot = client.request("GET", "/poc/self-permissions?project=projects/poc-sandbox")
        serialized = json.dumps(snapshot)
        assert credentials()["owner"]["email"] not in serialized, "Snapshot exposed another user's membership"
        assert "roles/workspaceAdmin" not in serialized, "Snapshot exposed unrelated role definitions"
        client.request("GET", "/v1/projects/poc-sandbox:getIamPolicy", statuses=(403,))
        results.append(f"{role}: management API denied; personal permission snapshot available")
    dev.request("GET", "/v1/projects/poc-prod", statuses=(403,))
    dev.request("GET", "/poc/self-permissions?project=projects/poc-prod", statuses=(403,))
    query(dev, "poc-prod", "prod_poc", "SELECT * FROM public.permission_fixture", (403,))
    selected = query(dev, "poc-sandbox", "sandbox_poc", "SELECT * FROM public.permission_fixture WHERE id = 1")
    assert "sandbox fixture" in json.dumps(selected), "Sandbox fixture data was not returned"
    query(dev, "poc-sandbox", "sandbox_poc", "CREATE TABLE public.permission_ddl (id integer PRIMARY KEY)")
    try:
        wait_database_metadata(owner, "poc-sandbox", "sandbox_poc", table="permission_ddl")
        query(dev, "poc-sandbox", "sandbox_poc", "SELECT * FROM public.permission_ddl")
    finally:
        query(dev, "poc-sandbox", "sandbox_poc", "DROP TABLE IF EXISTS public.permission_ddl")
    try:
        query(dev, "poc-sandbox", "sandbox_poc", "UPDATE public.permission_fixture SET value = 'sandbox updated' WHERE id = 1")
        changed = query(dev, "poc-sandbox", "sandbox_poc", "SELECT value FROM public.permission_fixture WHERE id = 1")
        assert "sandbox updated" in json.dumps(changed), "Sandbox DML did not change the fixture"
    finally:
        query(dev, "poc-sandbox", "sandbox_poc", "UPDATE public.permission_fixture SET value = 'sandbox fixture' WHERE id = 1")
    results.append("dev: sandbox SELECT/DDL/DML allowed; production inaccessible")
    for project, database in [("poc-sandbox", "sandbox_poc"), ("poc-prod", "prod_poc")]:
        query(leader, project, database, "SELECT * FROM public.permission_fixture", (403,))
        query(leader, project, database, "DELETE FROM public.permission_fixture WHERE id = 999", (403,))
        query(leader, project, database, "CREATE TABLE public.permission_blocked (id integer)", (403,))
        plan, issue = submit_change(leader, project, database)
        assert issue["plan"] == plan["name"], "Submitted issue did not reference its change plan"
        leader.request("POST", "/v1/" + plan["name"] + "/rollout", {}, (403,))
    results.append("leader: change issues accepted; standing SELECT, direct writes and rollout execution denied")
    expires = datetime.now(timezone.utc) + timedelta(seconds=5)
    binding = {"role": "roles/pocquery", "members": ["user:" + credentials()["leader"]["email"]],
               "condition": {"expression": f'request.time < timestamp("{expires.isoformat().replace("+00:00", "Z")}")'}}
    try:
        set_project_policy(owner, "poc-prod", bindings_for("poc-prod") + [binding])
        selected = query(leader, "poc-prod", "prod_poc", "SELECT * FROM public.permission_fixture WHERE id = 1")
        assert "production fixture" in json.dumps(selected), "Approved production fixture data was not returned"
        query(leader, "poc-prod", "prod_poc", "UPDATE public.permission_fixture SET value = 'blocked' WHERE id = 999", (403,))
        query(leader, "poc-prod", "prod_poc", "CREATE TABLE public.permission_blocked (id integer)", (403,))
        while datetime.now(timezone.utc) <= expires + timedelta(seconds=1):
            time.sleep(0.25)
        query(leader, "poc-prod", "prod_poc", "SELECT * FROM public.permission_fixture", (403,))
    finally:
        set_project_policy(owner, "poc-prod", bindings_for("poc-prod"))
    results.append("leader: owner-approved read grant works and expires without changing the login token")
    artifact = POC / "artifacts"
    artifact.mkdir(exist_ok=True)
    (artifact / "api-results.yaml").write_text(yaml.safe_dump({"passed": results}, allow_unicode=True))
    for result in results:
        log(result)
