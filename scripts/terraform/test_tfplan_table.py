"""Unit tests of tfplan_table: actions, changed fields and counts of a plan."""
import unittest

from tfplan_table import action_of, changed_fields, plan_rows, summary_meta


def rc(address, actions, before=None, after=None, after_unknown=None, mode="managed", change=None, **extra):
    """One entry of resource_changes, as `terraform show -json` prints it."""
    body = {"actions": actions, "before": before, "after": after, "after_unknown": after_unknown or {}}
    body.update(change or {})
    return {"address": address, "mode": mode, "change": body, **extra}


class ActionTest(unittest.TestCase):
    def test_plain_actions(self):
        for action in ("create", "update", "delete", "forget"):
            self.assertEqual(action_of(rc("a", [action])), action)

    def test_replace_in_either_order(self):
        self.assertEqual(action_of(rc("a", ["delete", "create"])), "replace")
        self.assertEqual(action_of(rc("a", ["create", "delete"])), "replace")

    def test_noop_import_and_move(self):
        self.assertEqual(action_of(rc("a", ["no-op"])), "no-op")
        self.assertEqual(action_of(rc("a", ["no-op"], change={"importing": {"id": "i-1"}})), "import")
        self.assertEqual(action_of(rc("a[0]", ["no-op"], previous_address="a")), "move")


class FieldsTest(unittest.TestCase):
    def test_update_lists_changed_top_level_keys(self):
        r = rc("a", ["update"], before={"x": 1, "y": {"k": 1}, "z": 3}, after={"x": 2, "y": {"k": 2}, "z": 3})
        self.assertEqual(changed_fields(r), ["x", "y"])

    def test_update_counts_values_known_after_apply(self):
        r = rc("a", ["update"], before={"x": 1, "arn": "old"}, after={"x": 1}, after_unknown={"arn": True})
        self.assertEqual(changed_fields(r), ["arn"])

    def test_update_counts_nested_unknown_values(self):
        r = rc("a", ["update"], before={"tags": {}}, after={"tags": {}}, after_unknown={"tags": {"id": True}})
        self.assertEqual(changed_fields(r), ["tags"])

    def test_replace_names_the_fields_that_force_it(self):
        r = rc("a", ["delete", "create"], before={"ami": "1", "x": 1}, after={"ami": "2", "x": 2},
               change={"replace_paths": [["ami"]]})
        self.assertEqual(changed_fields(r), ["ami"])

    def test_create_and_delete_have_no_fields(self):
        self.assertEqual(changed_fields(rc("a", ["create"], after={"x": 1})), [])
        self.assertEqual(changed_fields(rc("a", ["delete"], before={"x": 1})), [])

    def test_long_field_lists_are_capped(self):
        before = {f"k{i:02d}": 0 for i in range(12)}
        after = {k: 1 for k in before}
        fields = changed_fields(rc("a", ["update"], before=before, after=after))
        self.assertEqual(fields, [f"k{i:02d}" for i in range(8)] + ["+4"])


class TableTest(unittest.TestCase):
    def test_noop_and_data_sources_are_left_out(self):
        plan = {"resource_changes": [
            rc("data.aws_ami.x", ["read"], mode="data"),
            rc("aws_vpc.a", ["no-op"]),
            rc("aws_vpc.b", ["create"], after={"cidr_block": "10.0.0.0/16"}),
            rc("aws_vpc.c", ["update"], before={"tags": {}}, after={"tags": {"a": "1"}}),
        ]}
        self.assertEqual(plan_rows(plan), [["aws_vpc.b", "create", ""], ["aws_vpc.c", "update", "tags"]])

    def test_meta_mirrors_the_terraform_plan_line(self):
        plan = {"resource_changes": [
            rc("a", ["create"]),
            rc("b", ["delete", "create"]),
            rc("c", ["update"], before={"x": 1}, after={"x": 2}),
            rc("d", ["delete"]),
            rc("e", ["no-op"]),
            rc("f", ["no-op"], change={"importing": {"id": "1"}}),
            rc("g[0]", ["no-op"], previous_address="g"),
            rc("h", ["forget"]),
            rc("data.i", ["read"], mode="data"),
        ]}
        self.assertEqual(summary_meta(plan),
                         "2 add · 1 change · 2 destroy · 1 import · 1 move · 1 forget · 1 unchanged")

    def test_meta_of_an_empty_plan(self):
        self.assertEqual(summary_meta({}), "0 add · 0 change · 0 destroy")


if __name__ == "__main__":
    unittest.main()
