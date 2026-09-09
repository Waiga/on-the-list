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


def _wrap(
    text: str, indent: str = "", width: int = 78, hang: str | None = None
) -> list[str]:
    """Wrap to ``width``, indenting continuation lines by ``hang``.

    Without a hanging indent a wrapped item's second line starts level with
    the label in front of it and stops looking like one item.
    """
    words = text.split()
    lines: list[str] = []
    continuation = indent if hang is None else hang
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current.rstrip())
            current = continuation
        current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


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
        line = (
            f"{_plural(len(report.ingredients), 'ingredient')} read. "
            "Nothing found by the "
            f"{len(ran)} check{'s' if len(ran) != 1 else ''} that ran."
        )
        if report.considered:
            # Without this the reader meets a "considered and not counted"
            # section two lines after being told nothing was found, and has to
            # work out for themselves that the two agree.
            n = len(report.considered)
            line += (
                f" {n} ingredient{'s' if n != 1 else ''} did match an annex "
                f"entry and {'were' if n != 1 else 'was'} deliberately not "
                "counted; the reason is below."
            )
        return line
    parts = [f"{n} {name.replace('-', ' ')}" for name, n in counts.items()]
    return (
        f"{_plural(len(report.ingredients), 'ingredient')} read. "
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


#: How each annex is described in one word, for the entry list.
_ANNEX_IS = {
    "II": "prohibited",
    "III": "restricted",
    "IV": "a permitted colourant",
    "V": "a permitted preservative",
    "VI": "a permitted UV filter",
}


def entry_lines(report: Report) -> list[str]:
    """One line per ingredient the annexes name, with the entries naming it.

    This is the tool's own title, and for a while the report did not print it:
    a label containing Phenoxyethanol produced no finding, and the only trace
    of Annex V entry 29 was the coverage count saying one of three ingredients
    was named somewhere. The reader was told an ingredient was restricted and
    never told which annex, which entry, or under what product types.

    It is not a check. Nothing here is a finding and nothing here changes the
    exit code -- being named by an annex is the ordinary condition of a great
    many ingredients.
    """
    lines: list[str] = []
    seen: set[str] = set()
    for match in report.matches:
        if match.ingredient.raw in seen:
            continue
        seen.add(match.ingredient.raw)
        entries = [m.entry for m in report.matches if m.ingredient is match.ingredient]
        for entry in entries:
            what = _ANNEX_IS.get(entry.annex, entry.annex)
            line = f"  {match.ingredient.raw} — {entry.citation}, {what}"
            if entry.annex == "II" and entry.qualifier:
                line += f", with a condition ('{entry.qualifier}')"
            lines.append(line)
            if entry.product_types:
                types = " ".join(entry.product_types.split())
                lines.extend(
                    _wrap(
                        "limited to: " + (types[:150] + "..." if len(types) > 150 else types),
                        "        ",
                    )
                )
    return lines


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

    entries = entry_lines(report)
    if entries:
        out.append("WHAT THE ANNEXES NAME")
        out.extend(
            _wrap(
                "Every entry in Annexes II to VI that names an ingredient on "
                "this list. Being named is not a finding: Annexes III to VI "
                "are the restricted, permitted-colourant, "
                "permitted-preservative and permitted-UV-filter lists, and "
                "most cosmetics contain something on one of them.",
                "  ",
            )
        )
        out.append("")
        out.extend(entries)
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
            # Wrapped like everything else. A long reason used to run off the
            # right of a report every other line of which stops at 78 columns.
            # The reason is wrapped on its own so that the two-space column
            # after "not run" survives -- _wrap splits on whitespace and would
            # otherwise close it up.
            prefix = f"  not run  {run.name} — "
            wrapped = _wrap(run.reason, " " * len(prefix))
            wrapped[0] = prefix + wrapped[0].strip()
            out.extend(wrapped)
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
    entries = entry_lines(report)
    if entries:
        out.append("## What the annexes name")
        out.append("")
        for line in entries:
            out.append("-" + line[1:] if line.startswith("  ") and not line.startswith("        ") else "  " + line.strip())
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
        "annex_entries_naming_an_ingredient": [
            {
                "printed": match.ingredient.raw,
                "annex": match.entry.annex,
                "citation": match.entry.citation,
                "register_name": match.matched_name,
                "matched_on": match.via_kind,
                "chemical_name": match.entry.chemical_name,
                "product_types": " ".join(match.entry.product_types.split()),
                "conditions_and_warnings": " ".join(match.entry.wording.split()),
            }
            for match in report.matches
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
