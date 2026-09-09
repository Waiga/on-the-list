"""Render a report.

Written to be pasted into an email to whoever can act on it -- a formulator, a
regulatory adviser, a contract manufacturer -- so it leads with what was found,
names the register version it was found against, and ends by saying plainly
which checks ran and which did not.

The closing section is not boilerplate. A reader who sees four findings and no
statement of what was not examined will fill the gap in with an assumption, and
the assumption will be more generous than the evidence.
"""

from __future__ import annotations

import json

from on_the_list import __version__
from on_the_list.checks import CHECKS
from on_the_list.models import Report

_ABSENCE = (
    "Ingredients no annex entry names are counted as not restricted by these "
    "five annexes. That is all it means. Annexes II to VI list prohibited, "
    "restricted, permitted-colourant, permitted-preservative and permitted-"
    "UV-filter substances; they are not an inventory of valid INCI names. Aqua "
    "and Glycerin appear in none of them."
)


def _wrap(text: str, indent: str = "", width: int = 78) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current.rstrip())
            current = indent
        current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _headline(report: Report) -> str:
    if not report.parsed:
        return (
            "No ingredient list was found in this file, so nothing was "
            "compared against the annexes."
        )
    counts: dict[str, int] = {}
    for finding in report.findings:
        counts[finding.check] = counts.get(finding.check, 0) + 1
    if not counts:
        ran = [c.name for c in report.checks if c.ran]
        return (
            f"{len(report.ingredients)} ingredients read. Nothing found by the "
            f"{len(ran)} check{'s' if len(ran) != 1 else ''} that ran."
        )
    parts = [f"{n} {name.replace('-', ' ')}" for name, n in counts.items()]
    return (
        f"{len(report.ingredients)} ingredients read. "
        + ", ".join(parts)
        + "."
    )


_QUALIFIED_BLURB = (
    "These matched an Annex II entry whose own wording carries a condition -- "
    "\"except if the full refining history is known\", \"when used as a "
    "substance in hair dye products\", \"(nano)\". An ingredient list states "
    "none of those things, so this tool cannot tell whether the condition is "
    "met and does not guess. Each entry's wording is printed so you can read "
    "it yourself."
)

#: (heading for the text report, heading for markdown, the blurb under both).
#: Written out rather than derived, because deriving one from the other turned
#: "ANNEX II" into "Annex Ii".
_HEADINGS = {
    "prohibited": (
        "NAMES THAT MATCH AN ANNEX II ENTRY",
        "Names that match an Annex II entry",
        "Annex II is the list of substances prohibited in cosmetic products. "
        "A match is reported here as a match. Whether it means anything about "
        "this product is for someone with the formulation in front of them.",
    ),
    "colourant-order": (
        "COLOURANTS PRINTED BEFORE OTHER INGREDIENTS",
        "Colourants printed before other ingredients",
        "Where a colour index number sits in the list. Nothing more.",
    ),
    "repeated-entry": (
        "NAMES THAT APPEAR MORE THAN ONCE",
        "Names that appear more than once",
        "A property of the list on its own; no annex is involved.",
    ),
    "warning-wording": (
        "ANNEX WORDING NOT FOUND IN THE PACK TEXT SUPPLIED",
        "Annex wording not found in the pack text supplied",
        "A gap between two documents, not a finding about the pack. The "
        "wording may be printed somewhere the supplied text does not cover.",
    ),
}


def render_text(report: Report) -> str:
    out: list[str] = [f"on-the-list {__version__} — {report.source or 'label'}"]
    out.append(report.register.line())
    out.append("")
    out.extend(_wrap(_headline(report)))
    out.append("")

    for check in CHECKS:
        found = [f for f in report.findings if f.check == check]
        if not found:
            continue
        title, _, blurb = _HEADINGS[check]
        out.append(title)
        out.extend(_wrap(blurb, "  "))
        out.append("")
        plain = [f for f in found if not f.qualified]
        qualified = [f for f in found if f.qualified]
        for finding in plain:
            out.extend(_wrap(finding.summary, "  "))
            for line in finding.detail:
                out.extend(_wrap(line, "      "))
            out.append("")
        if qualified:
            if plain:
                out.append("  — and where the annex entry sets a condition —")
            out.extend(_wrap(_QUALIFIED_BLURB, "  "))
            out.append("")
            for finding in qualified:
                out.extend(_wrap(finding.summary, "  "))
                for line in finding.detail:
                    out.extend(_wrap(line, "      "))
                out.append("")

    if report.considered:
        out.append("CONSIDERED AND NOT COUNTED")
        out.extend(
            _wrap(
                "These ingredients matched an annex entry and are not reported "
                "above. They are listed so you can see the tool noticed them.",
                "  ",
            )
        )
        out.append("")
        for item in report.considered:
            out.extend(_wrap(item.ingredient.raw, "  "))
            out.extend(_wrap(item.reason, "      "))
            out.append("")

    if report.parsed:
        out.append("COVERAGE")
        out.extend(
            _wrap(
                f"{len(report.unrestricted)} of {len(report.ingredients)} "
                "ingredients are not named by any entry in Annexes II to VI.",
                "  ",
            )
        )
        out.extend(_wrap(_ABSENCE, "  "))
        out.append("")

    if report.limits:
        out.append("WHAT LIMITED THIS RUN")
        for limit in report.limits:
            out.extend(_wrap(limit, "  "))
        out.append("")

    out.append("CHECKS")
    for run in report.checks:
        if run.ran:
            out.append(f"  ran      {run.name} — {run.findings} found")
        else:
            out.append(f"  not run  {run.name} — {run.reason}")
    out.append("")
    out.extend(
        _wrap(
            "Nothing here is a statement that this product is compliant, "
            "safe, legal or acceptable to a retailer. This tool compares "
            "names on a label with names in a published annex. It cannot see "
            "concentration, product type, impurities, or the formulation.",
            "  ",
        )
    )
    return "\n".join(out).rstrip() + "\n"


def render_markdown(report: Report) -> str:
    out = [f"# on-the-list {__version__} — {report.source or 'label'}", ""]
    out.append(f"*{report.register.line()}*")
    out.append("")
    out.append(_headline(report))
    out.append("")
    for check in CHECKS:
        found = [f for f in report.findings if f.check == check]
        if not found:
            continue
        _, title, blurb = _HEADINGS[check]
        out.append(f"## {title}")
        out.append("")
        out.append(blurb)
        out.append("")
        # Unconditional findings first, as in the text report.
        for finding in sorted(found, key=lambda f: f.qualified):
            mark = (
                " *(the annex entry sets a condition)*" if finding.qualified else ""
            )
            out.append(f"- **{finding.summary}**{mark}")
            for line in finding.detail:
                out.append(f"  - {line}")
        out.append("")
        if any(f.qualified for f in found):
            out.append(_QUALIFIED_BLURB)
            out.append("")
    if report.considered:
        out.append("## Considered and not counted")
        out.append("")
        out.append(
            "These matched an annex entry and are not reported above. They are "
            "listed so you can see the tool noticed them."
        )
        out.append("")
        for item in report.considered:
            out.append(f"- **{item.ingredient.raw}** — {item.reason}")
        out.append("")
    if report.parsed:
        out.append("## Coverage")
        out.append("")
        out.append(
            f"{len(report.unrestricted)} of {len(report.ingredients)} "
            "ingredients are not named by any entry in Annexes II to VI. "
            + _ABSENCE
        )
        out.append("")
    out.append("## Checks")
    out.append("")
    for run in report.checks:
        state = f"ran, {run.findings} found" if run.ran else f"not run: {run.reason}"
        out.append(f"- `{run.name}` — {state}")
    out.append("")
    out.append(
        "Nothing here is a statement that this product is compliant, safe, "
        "legal or acceptable to a retailer."
    )
    return "\n".join(out).rstrip() + "\n"


def render_json(report: Report) -> str:
    payload = {
        "tool": "on-the-list",
        "version": __version__,
        "source": report.source,
        "register": {
            "origin": report.register.origin,
            "distinct_names": report.register.name_count,
            "annexes": {
                annex: {
                    "last_update": last,
                    "sha256": digest,
                    "entries": rows,
                }
                for annex, (last, digest, rows) in report.register.annexes.items()
            },
        },
        "ingredient_list_parsed": report.parsed,
        "ingredients": [
            {
                "printed": item.raw,
                "normalised": item.normalised,
                "index": item.index,
                "position": item.position,
            }
            for item in report.ingredients
        ],
        "findings": [
            {
                "check": finding.check,
                "summary": finding.summary,
                "detail": list(finding.detail),
                "citation": finding.citation,
                "annex_entry_sets_a_condition": finding.qualified,
            }
            for finding in report.findings
        ],
        "considered_and_not_counted": [
            {
                "printed": item.ingredient.raw,
                "citation": item.entry.citation,
                "reason": item.reason,
            }
            for item in report.considered
        ],
        "checks": [
            {
                "name": run.name,
                "ran": run.ran,
                "reason": run.reason,
                "findings": run.findings,
            }
            for run in report.checks
        ],
        "not_restricted_by_these_annexes": [
            item.raw for item in report.unrestricted
        ],
        "limits": report.limits,
        "disclaimer": (
            "This output is a comparison of names on a label with names in "
            "Annexes II to VI of Regulation (EC) No 1223/2009 as published by "
            "the European Commission. It is not a statement about compliance, "
            "safety or legality."
        ),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def render_checks() -> str:
    lines = ["on-the-list checks", ""]
    for name, description in CHECKS.items():
        lines.append(f"  {name}")
        lines.extend(_wrap(description, "      "))
        lines.append("")
    lines.extend(
        _wrap(
            "Switch any of them off with --skip NAME, repeated as needed. The "
            "report always states which ran.",
            "  ",
        )
    )
    return "\n".join(lines).rstrip() + "\n"
