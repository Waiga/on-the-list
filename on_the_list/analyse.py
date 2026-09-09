"""Turn label text into a report. The whole analysis path starts here.

This module and everything it imports are the offline half of the package.
``tests/test_offline.py`` reads their source and fails if any of them gains the
ability to open a connection or start a process, and separately runs a real
analysis with sockets disabled. Downloading a register lives in ``fetch``,
which nothing here imports.
"""

from __future__ import annotations

from on_the_list import checks as check_mod
from on_the_list import ingredients as ing
from on_the_list.models import Report
from on_the_list.register import Register


def analyse(
    *,
    label_text: str = "",
    ingredients_text: str = "",
    pack_text: str = "",
    register: Register,
    source: str = "",
    skip: frozenset[str] = frozenset(),
) -> Report:
    """Read a label and report what the annexes say about it.

    ``label_text`` is a whole label, from which the ingredient block is
    located. ``ingredients_text`` is the block itself, for when the caller
    already has it. ``pack_text`` is everything printed on the pack, which the
    warning-wording check searches; when a whole label was supplied it is used
    for that too, since the warnings are printed on the same pack.
    """
    limits: list[str] = []
    parsed = False
    block = ""

    if ingredients_text.strip():
        if ing.looks_binary(ingredients_text):
            limits.append(
                "The file supplied as an ingredient list is not printable "
                "text. Nothing was parsed from it."
            )
        else:
            block, dropped = ing.trim(ingredients_text)
            parsed = bool(block.strip())
            if dropped.strip():
                limits.append(
                    "What was supplied continues past the ingredient list into "
                    "another pack panel. Everything from here on was not read "
                    f"as ingredients: {' '.join(dropped.split())[:110]}"
                )
    elif label_text.strip():
        if ing.looks_binary(label_text):
            limits.append(
                "The file supplied is not printable text. Nothing was parsed "
                "from it."
            )
        else:
            block, parsed = ing.extract(label_text)
            if not parsed:
                limits.append(
                    "No ingredient list was found: the text has no heading "
                    "this tool recognises, in any of the languages it knows. "
                    "Pass the list itself with --ingredients if you have it."
                )

    items = ing.parse(block) if parsed else []
    if parsed and not items:
        parsed = False
        limits.append(
            "An ingredient heading was found but nothing under it parsed into "
            "ingredients."
        )

    headings = ing.component_headings(block) if parsed else []
    if headings:
        limits.append(
            "This ingredient field carries "
            f"{len(headings)} section "
            f"{'heading' if len(headings) == 1 else 'headings'} -- "
            + ", ".join(f"'{h}'" for h in headings[:4])
            + (" and others" if len(headings) > 4 else "")
            + ". A multi-component pack declares one list per component in the "
            "same field, and a pack panel printed inside it has the same "
            "effect: what was parsed is not one product's ingredient order. "
            "The two checks that depend on that order did not run."
        )

    # Both, when both were given. A whole label file is pack text; a separate
    # --pack-text file adds to it rather than replacing it, because the panel
    # carrying a warning is often not the panel carrying the list.
    searchable = "\n".join(part for part in (pack_text, label_text) if part.strip())
    findings, runs, matches, unrestricted, not_searched, considered = check_mod.run(
        items,
        register,
        searchable if parsed else "",
        skip=skip,
        one_list=not headings,
    )
    if not parsed:
        runs = [
            run
            if not run.ran
            else type(run)(
                run.name,
                False,
                "there was no ingredient list to check.",
            )
            for run in runs
        ]
        findings = []
        considered = []

    if not_searched:
        shown = ", ".join(not_searched[:8])
        more = (
            f", and {len(not_searched) - 8} more"
            if len(not_searched) > 8
            else ""
        )
        limits.append(
            f"{len(not_searched)} annex "
            f"{'entry' if len(not_searched) == 1 else 'entries'} matched here "
            "attach conditions of use or warning wording in a form this tool "
            f"does not search for, so they were not checked: {shown}{more}. "
            "Open the entry to read what it says."
        )

    prose = [i for i in items if ing.looks_like_prose(i)]
    if prose:
        limits.append(
            f"{len(prose)} of the {len(items)} entries read are longer than "
            "any INCI name, so this panel almost certainly contains pack prose "
            "-- a warning, a distributor address, a second product's list -- "
            "parsed as ingredients. Every count below is affected. The first "
            f"is: {prose[0].raw[:90]}"
        )

    declared = [i for i in items if i.position == "declared"]
    if parsed and any(i.position == "may-contain" for i in items):
        limits.append(
            "The list has a 'may contain' block. Its contents are printed "
            "across a whole shade range, so the position check ignores it "
            f"and read only the {len(declared)} declared entries."
        )

    return Report(
        source=source,
        ingredients=items,
        parsed=parsed,
        findings=findings,
        checks=runs,
        matches=matches,
        register=register.info,
        unrestricted=unrestricted,
        considered=considered,
        limits=limits,
        pack_text_supplied=bool(searchable.strip()),
    )
