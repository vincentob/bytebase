#!/usr/bin/env python3
"""Summary table of a saved Terraform plan, printed after the native plan output.

    Terraform 计划  1 add · 1 change · 0 destroy · 42 unchanged

      资源地址                操作    变更字段
      ----------------------  ------  -------------------
      aws_instance.web        update  instance_type, tags
      aws_security_group.web  create

One row per managed resource that changes; unchanged resources and data sources
are only counted in the title. Only field names are shown, never values, so the
table stays safe to share when the plan touches secrets.

Usage: tfplan_table.py PLAN_FILE
Template: ~/.claude/templates/tfplan_table.py, copied into scripts/terraform/
next to table.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter

from table import CYAN, GREEN, RED, YELLOW, section

MAX_FIELDS = 8
COLOURS = {"create": GREEN, "update": YELLOW, "delete": RED, "replace": RED,
           "import": CYAN, "move": CYAN, "forget": CYAN}
EXTRA_COUNTS = ("import", "move", "forget")


def action_of(resource: dict) -> str:
    """One word per resource: create, update, delete, replace, import, move, forget or no-op."""
    change = resource["change"]
    actions = change["actions"]
    if set(actions) == {"create", "delete"}:
        return "replace"
    if actions == ["no-op"]:
        if change.get("importing"):
            return "import"
        if resource.get("previous_address"):
            return "move"
    return actions[0]


def _has_unknown(value: object) -> bool:
    if isinstance(value, dict):
        return any(_has_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_unknown(v) for v in value)
    return value is True


def changed_fields(resource: dict) -> list[str]:
    """Top-level attribute names that change, capped at MAX_FIELDS; values are never read out."""
    action = action_of(resource)
    change = resource["change"]
    if action == "replace" and change.get("replace_paths"):
        names = {str(path[0]) for path in change["replace_paths"] if path}
    elif action in ("update", "replace"):
        before, after = change.get("before") or {}, change.get("after") or {}
        names = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
        names |= {key for key, value in (change.get("after_unknown") or {}).items() if _has_unknown(value)}
    else:
        return []
    ordered = sorted(names)
    if len(ordered) > MAX_FIELDS:
        return ordered[:MAX_FIELDS] + [f"+{len(ordered) - MAX_FIELDS}"]
    return ordered


def _managed(plan: dict) -> list[dict]:
    return [r for r in plan.get("resource_changes", []) if r.get("mode") == "managed"]


def plan_rows(plan: dict) -> list[list[str]]:
    """[address, action, fields] for every managed resource that is not a no-op."""
    rows = []
    for resource in _managed(plan):
        action = action_of(resource)
        if action != "no-op":
            rows.append([resource["address"], action, ", ".join(changed_fields(resource))])
    return rows


def summary_meta(plan: dict) -> str:
    """Counts in the words of Terraform's own `Plan:` line, then the extras that occur."""
    resources = _managed(plan)
    counts = Counter(action_of(r) for r in resources)
    imports = sum(1 for r in resources if r["change"].get("importing"))
    parts = [f"{counts['create'] + counts['replace']} add",
             f"{counts['update']} change",
             f"{counts['delete'] + counts['replace']} destroy"]
    extras = {"import": imports, "move": counts["move"], "forget": counts["forget"],
              "unchanged": counts["no-op"]}
    parts += [f"{n} {name}" for name, n in extras.items() if n]
    return " · ".join(parts)


def load_plan(path: str) -> dict:
    result = subprocess.run(["terraform", "show", "-json", "-no-color", path], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"terraform show failed (exit {result.returncode})")
    return json.loads(result.stdout)


def print_table(plan: dict) -> None:
    rows = plan_rows(plan)
    section("Terraform 计划", ["资源地址", "操作", "变更字段"], rows, meta=summary_meta(plan),
            row_colour=lambda i: COLOURS.get(rows[i][1], ""))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: tfplan_table.py PLAN_FILE", file=sys.stderr)
        return 2
    try:
        plan = load_plan(argv[1])
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print_table(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
