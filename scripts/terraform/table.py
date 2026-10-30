"""House terminal table, the format every make target prints tables in.

    Title  dim stats                       <- cyan bold title, dim context

      HEADER     HEADER  AMOUNT            <- 2-space indent, bold header
      ---------  ------  ------            <- dashed rule, one run per column
      text left  x        1.50             <- 2-space gap; numeric columns (header too) right
                 y       12.00             <- a value repeating the row above is blanked

Rules: widths count display cells (CJK = 2); colour is off when stdout is not a
terminal or NO_COLOR is set; an empty table prints a dim "(none)"; a status
colour paints the whole row; a TOTAL row is bold; footnotes are dim and
indented. Copy this file into scripts/<group>/ and import section().
"""
from __future__ import annotations

import os
import sys
import unicodedata
from typing import Callable, Sequence

_COLOUR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
OFF, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[36m"
INDENT, GAP, NONE = "  ", "  ", "(none)"


def paint(code: str, text: str) -> str:
    return f"{code}{text}{OFF}" if _COLOUR and code else text


def width(text: str) -> int:
    """Display cells: East Asian wide and fullwidth characters take two."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _numeric(cell: str) -> bool:
    try:
        float(cell.replace(",", ""))
        return True
    except ValueError:
        return False


def lines(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    """Header, rule and rows as plain strings, indent included, no colour."""
    body = [[str(c) for c in r] + [""] * (len(header) - len(r)) for r in rows]
    widths = [max([width(h)] + [width(r[i]) for r in body]) for i, h in enumerate(header)]
    numeric = [
        any(r[i] not in ("", "-") for r in body)
        and all(_numeric(r[i]) for r in body if r[i] not in ("", "-"))
        for i in range(len(header))
    ]

    def pad(cells: Sequence[str], right: Sequence[bool]) -> str:
        parts = [(" " * (w - width(c)) + c) if r else (c + " " * (w - width(c)))
                 for c, w, r in zip(cells, widths, right)]
        return (INDENT + GAP.join(parts)).rstrip()

    return ([pad(header, numeric),
             INDENT + GAP.join("-" * w for w in widths)]
            + [pad(r, numeric) for r in body])


def blank_repeats(rows: Sequence[Sequence[object]], col: int = 0) -> list[list[object]]:
    """Blank a grouping cell that repeats the row above, so groups read."""
    out, previous = [], object()
    for r in rows:
        row = list(r)
        current, row[col] = row[col], "" if row[col] == previous else row[col]
        previous = current
        out.append(row)
    return out


def section(title: str, header: Sequence[str], rows: Sequence[Sequence[object]],
            meta: str = "", row_colour: Callable[[int], str] | None = None) -> None:
    """Print a titled table: blank line, title, blank line, table."""
    print()
    print(paint(CYAN + BOLD, title) + (f"  {paint(DIM, meta)}" if meta else ""))
    print()
    if not rows:
        print(INDENT + paint(DIM, NONE))
        return
    head, rule, *body = lines(header, rows)
    print(paint(BOLD, head))
    print(rule)
    for i, line in enumerate(body):
        code = row_colour(i) if row_colour else ""
        if str(rows[i][0]) == "TOTAL" and not code:
            code = BOLD
        print(paint(code, line))


def footnote(text: str) -> None:
    print(f"\n{INDENT}{paint(DIM, text)}")


if __name__ == "__main__":
    section("Suppliers", ["PROVIDER", "状态", "PAID"],
            [["starchasing", "启用", "24.06"], ["zai", "停用", "3.5"], ["TOTAL", "", "27.56"]],
            meta="2 suppliers, 1 enabled",
            row_colour=lambda i: [GREEN, YELLOW, ""][i])
    footnote("来源：config.yaml")
