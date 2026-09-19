"""The four checks, and the coverage count.

Each one is a comparison between something printed on the label the user
supplied and something printed in an annex. Neither side is inferred, and no
check produces a verdict. "This ingredient's name appears in Annex II" is a
fact about two strings. "This product is illegal" is not something a text
comparison can know, and nothing here says it.

Every check can be switched off on its own, and the report always states which
ones ran. A check that did not run must never read as a check that found
nothing.
"""

from __future__ import annotations

from on_the_list.models import (
    AnnexEntry,
    CheckRun,
    Exclusion,
    Finding,
    Ingredient,
    Match,
)
from on_the_list.normalise import fold, is_colour_index
from on_the_list.register import Register

#: Every check, in report order, with the one-line description printed by
#: ``--list-checks``.
CHECKS: dict[str, str] = {
    "prohibited": (
        "an ingredient's name matches an entry in Annex II, the list of "
        "substances prohibited in cosmetic products"
    ),
    "colourant-order": (
        "a CI-numbered colourant is printed before a non-colourant, where the "
        "Regulation allows colourants in any order after the other ingredients"
    ),
    "repeated-entry": "the same name appears twice in the declared list",
    "warning-wording": (
        "an annex attaches a 'Contains ...' statement to an ingredient on the "
        "list and that statement was not found in the pack text supplied"
    ),
}


def match_ingredients(
    ingredients: list[Ingredient], register: Register
) -> tuple[list[Match], list[Ingredient]]:
    """Pair each ingredient with every annex entry naming it.

    Returns the matches and the ingredients no entry named. The second list is
    called *unrestricted*, never *unknown* and never *unrecognised*: the
    annexes are lists of restricted substances, not an inventory of valid
    ones. Aqua and Glycerin are in none of them.
    """
    matches: list[Match] = []
    unrestricted: list[Ingredient] = []
    for ingredient in ingredients:
        found: list[Match] = []
        candidates = [("as printed", "as printed", ingredient.normalised)]
        candidates.extend(
            (alias, kind, fold(alias)) for alias, kind in ingredient.aliases
        )
        for via, kind, folded in candidates:
            for entry in register.lookup(folded):
                if any(
                    existing.entry is entry and existing.ingredient is ingredient
                    for existing in found
                ):
                    continue
                name, source = next(
                    (pair for pair in entry.normalised_names if pair[0] == folded),
                    (folded, "identified"),
                )
                printed = next(
                    (
                        original
                        for original in entry.names
                        if fold(original) == folded
                    ),
                    folded,
                )
                found.append(
                    Match(
                        ingredient=ingredient,
                        entry=entry,
                        matched_name=printed,
                        source=source,  # type: ignore[arg-type]
                        via=via,
                        via_kind=kind,
                    )
                )
        if found:
            matches.extend(found)
        else:
            unrestricted.append(ingredient)
    return matches, unrestricted


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(
        n % 10, "th"
    )
    return f"{n}{suffix}"


def _entry_line(entry: AnnexEntry) -> str:
    name = entry.chemical_name or (entry.names[0] if entry.names else "")
    return f"{entry.citation}: {name}" if name else entry.citation


def check_prohibited(
    matches: list[Match],
) -> tuple[list[Finding], list[Exclusion]]:
    """Check 1. A name on the list matches an Annex II entry.

    Annex II is the list of substances prohibited in cosmetic products. A match
    is reported as a match, with the entry number, so that whoever reads it can
    open the annex and decide. It is not reported as a violation. An INCI name
    can be shared by a permitted and a prohibited form, an entry can be limited
    to a route of exposure the list does not state, and a crowd-sourced or
    mistyped ingredient list is a real possibility.
    """
    findings: list[Finding] = []
    excluded: list[Exclusion] = []
    for match in matches:
        if match.entry.annex != "II":
            continue
        if match.via_kind == "part":
            # The name matched a bracketed or slash-separated part of what is
            # printed, not the whole of it. That is how a colourant is found
            # inside "Titanium Dioxide (CI 77891)", and it is useful there. It
            # is not good enough for a prohibited-substances list: over 16,635
            # real labels it produced "CI 77288 / CHROMIUM" against the entry
            # for chromium metal and "Styrene (Acrylate Copolymer)" against the
            # entry for the styrene monomer, and no correct finding at all.
            excluded.append(
                Exclusion(
                    ingredient=match.ingredient,
                    entry=match.entry,
                    reason=(
                        f"{match.entry.citation} names "
                        f"'{match.matched_name}', which is part of what is "
                        f"printed here rather than the whole of it. A match on "
                        "a fragment is not reported against Annex II."
                    ),
                )
            )
            continue
        if match.entry.nano_only and "nano" not in match.ingredient.raw.lower():
            excluded.append(
                Exclusion(
                    ingredient=match.ingredient,
                    entry=match.entry,
                    reason=(
                        f"{match.entry.citation} is about the nanomaterial "
                        f"form (its own name reads "
                        f"'{' '.join(match.entry.chemical_name.split())}') "
                        "while listing the ordinary INCI name beside it. This "
                        "label does not say nano, so the entry is not about "
                        "what is printed here."
                    ),
                )
            )
            continue
        detail = [
            f"printed as: {match.ingredient.raw}",
            f"register name: {match.matched_name} "
            f"(read from the '{match.source}' column)",
        ]
        if match.entry.chemical_name:
            detail.append(f"annex entry: {match.entry.chemical_name}")
        # An Annex II entry is frequently qualified by another annex --
        # Hydroquinone is prohibited "with the exception of entry 14 in Annex
        # III", where it is permitted in professional nail products. Reporting
        # only the prohibition, when the same name also appears in a
        # permitted-use annex, would be a half-truth. Both are printed.
        elsewhere = [
            other.entry
            for other in matches
            if other.ingredient is match.ingredient and other.entry.annex != "II"
        ]
        if elsewhere:
            detail.append(
                "the same name also appears in "
                + ", ".join(sorted({e.citation for e in elsewhere}))
                + ", which sets out conditions under which it is allowed. Read "
                "the Annex II entry's own wording: several are prohibitions "
                "qualified by exactly such an entry."
            )
        findings.append(
            Finding(
                check="prohibited",
                summary=(
                    f"{match.ingredient.raw} matches {match.entry.citation}, "
                    + (
                        "whose own wording is conditional "
                        f"(it says '{match.entry.qualifier}')."
                        if match.entry.qualifier
                        else "in the Commission's list of substances "
                        "prohibited in cosmetic products."
                    )
                ),
                detail=tuple(detail),
                citation=match.entry.citation,
                qualified=bool(match.entry.qualifier),
            )
        )
    return findings, excluded


def check_colourant_order(
    ingredients: list[Ingredient], register: Register
) -> list[Finding]:
    """Check 2. A CI-numbered colourant printed before a non-colourant.

    Article 19(1)(g) of Regulation (EC) No 1223/2009 lets colourants be listed
    in any order *after* the other ingredients. A colourant sitting in the
    middle of the list is therefore a positional observation with no judgement
    in it, and it is reported as one.

    Deliberately restricted to bare ``CI NNNNN`` entries. Named substances in
    Annex IV are not used, because most of them do more than one job: Titanium
    Dioxide is an Annex IV colourant, an Annex VI UV filter and an opacifier,
    and its position in a list proves nothing about which of those it is doing.
    A ``CI`` number is unambiguous. That narrowing costs coverage and buys the
    only thing that makes a positional finding worth printing.

    The 'may contain' block is skipped entirely: it is printed across a whole
    shade range and its order carries no information.
    """
    declared = [i for i in ingredients if i.position == "declared"]
    colour_names = register.colour_index_names
    findings: list[Finding] = []

    def is_colourant(item: Ingredient) -> bool:
        # "CI 77891 / TITANIUM DIOXIDE" and "Iron Oxides (CI 77491)" are
        # colourants printed under two names. Counting them as non-colourants
        # made every colourant in front of them look mis-positioned.
        if is_colour_index(item.normalised):
            return True
        return any(is_colour_index(fold(alias)) for alias, _ in item.aliases)

    # How many non-colourants follow each position, computed once. Rebuilding
    # the tail inside the loop was quadratic: a list of 20,000 colour index
    # numbers took 64 seconds and produced a 4 MB report.
    tail: list[int] = [0] * (len(declared) + 1)
    first_after: list[Ingredient | None] = [None] * (len(declared) + 1)
    for position in range(len(declared) - 1, -1, -1):
        item = declared[position]
        if is_colourant(item):
            tail[position] = tail[position + 1]
            first_after[position] = first_after[position + 1]
        else:
            tail[position] = tail[position + 1] + 1
            first_after[position] = item

    for position, ingredient in enumerate(declared):
        if not is_colour_index(ingredient.normalised):
            continue
        if ingredient.normalised not in colour_names:
            # A CI number the annexes do not list. Reported by the coverage
            # count, not here: an unlisted colourant is not a position problem.
            continue
        count = tail[position + 1]
        if not count:
            continue
        following = first_after[position + 1]
        entries = register.lookup(ingredient.normalised)
        entry = entries[0]
        # Four colour index numbers in the register appear only in Annex II --
        # CI 12150, CI 20170, CI 27290 and CI 45425, each prohibited in hair
        # dye products. Saying "listed in Annex IV as a colourant" about one of
        # those is an assertion the data does not support, and the same report
        # cited Annex II for it two sections earlier.
        where = ", ".join(sorted({e.citation for e in entries}))
        findings.append(
            Finding(
                check="colourant-order",
                summary=(
                    f"{ingredient.raw} is a colour index number named in "
                    f"{where}, and is printed {_ordinal(ingredient.index)}, "
                    "before "
                    + (
                        "one entry that is not a colour index number."
                        if count == 1
                        else f"{count} entries that are not colour index "
                        "numbers."
                    )
                ),
                detail=(
                    "the first of those is: "
                    + (following.raw if following else ""),
                    "Article 19(1)(g) allows colourants in any order after the "
                    "other ingredients, so their position is normally the end "
                    "of the list. This is a statement about where the name is "
                    "printed and nothing else.",
                    "It does not hold for hair colourants, which are not "
                    "covered by that allowance, and an ingredient below 1% may "
                    "be listed in any order in any case.",
                ),
                citation=entry.citation,
            )
        )
    return findings


def check_repeated(ingredients: list[Ingredient]) -> list[Finding]:
    """Check 3. The same name twice in the declared list.

    Needs no register at all: it is a property of the list on its own.

    A whole list printed twice is a different thing from an ingredient repeated
    once, and packs really are printed with the list in two languages, or with
    the same panel captured twice by an importer. When most of the declared
    entries are repeats, that is reported as one finding about the list rather
    than as thirty findings about thirty ingredients.
    """
    declared = [i for i in ingredients if i.position == "declared"]
    seen: dict[str, list[Ingredient]] = {}
    for ingredient in declared:
        seen.setdefault(ingredient.normalised, []).append(ingredient)
    repeated = {
        name: items for name, items in seen.items() if len(items) > 1
    }
    if not repeated:
        return []

    duplicated = sum(len(items) - 1 for items in repeated.values())
    if declared and duplicated >= max(4, len(declared) // 3):
        return [
            Finding(
                check="repeated-entry",
                summary=(
                    f"{duplicated} of the {len(declared)} entries in the "
                    "declared list repeat an earlier entry. A list this "
                    "repetitive is usually the same panel printed more than "
                    "once, in two languages or captured twice, rather than "
                    "ingredients genuinely declared twice."
                ),
                detail=tuple(
                    f"{name} appears {len(items)} times"
                    for name, items in sorted(
                        repeated.items(), key=lambda kv: -len(kv[1])
                    )[:8]
                ),
            )
        ]

    findings = []
    for name, items in repeated.items():
        places = ", ".join(str(item.index) for item in items)
        findings.append(
            Finding(
                check="repeated-entry",
                summary=(
                    f"{items[0].raw} appears {len(items)} times in the "
                    f"declared list, at positions {places}."
                ),
                detail=(
                    "An ingredient list gives each ingredient once, in "
                    "descending order of weight. Two entries folding to the "
                    "same name may also be two different spellings the tool "
                    "cannot tell apart.",
                ),
            )
        )
    return findings


def check_warning_wording(
    matches: list[Match], pack_text: str
) -> tuple[list[Finding], list[str]]:
    """Check 4. A ``Contains ...`` statement not found in the pack text.

    Returns the findings and a list of entries whose wording was **not**
    searched for, which the report prints alongside them.

    This is reported as a gap, not as a violation, and the distinction is not a
    hedge. The wording may be printed somewhere on the pack that the supplied
    text does not cover, or in another language, or the annex entry's
    conditions may not apply to this product at all -- many of them are limited
    by product type or by a concentration that no ingredient list states.

    Only ``Contains ...`` statements are searched for. See
    ``annexes.label_phrases`` for why, and for what that leaves out.
    """
    haystack = fold(pack_text)
    findings: list[Finding] = []
    not_searched: list[str] = []
    reported: set[tuple[str, str]] = set()
    for match in matches:
        entry = match.entry
        if not entry.wording:
            continue
        if not entry.label_phrases:
            # Named compactly. Printing each entry's full chemical name here
            # produced twenty lines of naphthalenesulphonate for one lipstick,
            # which buries the findings above it.
            line = f"{match.ingredient.raw} ({entry.citation})"
            if line not in not_searched:
                not_searched.append(line)
            continue
        for phrase in entry.label_phrases:
            key = (entry.citation, phrase)
            if key in reported:
                continue
            if fold(phrase) in haystack:
                continue
            reported.add(key)
            detail = [
                f"the annex attaches this to: {match.ingredient.raw}",
                f"the wording is: {phrase}",
                "It was not found in the text supplied. That is a gap in what "
                "was supplied, not a finding about the pack: the wording may "
                "be printed elsewhere on it, or in another language, and the "
                "entry's conditions may not apply to this product.",
            ]
            if entry.product_types:
                detail.append(
                    "the entry is limited to: "
                    + " ".join(entry.product_types.split())
                )
            # The full wording, so the reader can see for themselves whether
            # the statement is conditional. Several are: Annex III entry 4
            # reads "Above 2%: Contains ammonia", and Annex VI entry 4
            # footnotes Benzophenone-3 as not required at 0,5 % or less. An
            # ingredient list does not state a concentration, so this tool
            # cannot tell whether such a condition is met, and it does not try.
            whole = " ".join(entry.wording.split())
            detail.append(
                "the entry's wording in full: "
                + (whole if len(whole) <= 400 else whole[:397] + "...")
            )
            findings.append(
                Finding(
                    check="warning-wording",
                    summary=(
                        f"{entry.citation} attaches the statement "
                        f"'{phrase}' to {match.ingredient.raw}, and that "
                        "statement is not in the pack text supplied."
                    ),
                    detail=tuple(detail),
                    citation=entry.citation,
                )
            )
    return findings, not_searched


def run(
    ingredients: list[Ingredient],
    register: Register,
    pack_text: str | None,
    skip: frozenset[str] = frozenset(),
    one_list: bool = True,
) -> tuple[
    list[Finding],
    list[CheckRun],
    list[Match],
    list[Ingredient],
    list[str],
    list[Exclusion],
]:
    """Run every check that is switched on. Returns everything the report needs."""
    matches, unrestricted = match_ingredients(ingredients, register)
    findings: list[Finding] = []
    runs: list[CheckRun] = []
    not_searched: list[str] = []
    considered: list[Exclusion] = []

    def record(name: str, produced: list[Finding]) -> None:
        findings.extend(produced)
        runs.append(CheckRun(name=name, ran=True, findings=len(produced)))

    if "prohibited" in skip:
        runs.append(CheckRun("prohibited", False, "switched off with --skip"))
    else:
        produced, considered = check_prohibited(matches)
        record("prohibited", produced)

    _MANY = (
        "the ingredient field holds more than one section (a second "
        "component's list, or a pack panel), so the order of what was parsed "
        "is not one product's ingredient order. See the limits above."
    )
    if "colourant-order" in skip:
        runs.append(
            CheckRun("colourant-order", False, "switched off with --skip")
        )
    elif not one_list:
        runs.append(CheckRun("colourant-order", False, _MANY))
    else:
        record("colourant-order", check_colourant_order(ingredients, register))

    if "repeated-entry" in skip:
        runs.append(
            CheckRun("repeated-entry", False, "switched off with --skip")
        )
    elif not one_list:
        runs.append(CheckRun("repeated-entry", False, _MANY))
    else:
        record("repeated-entry", check_repeated(ingredients))

    if "warning-wording" in skip:
        runs.append(
            CheckRun("warning-wording", False, "switched off with --skip")
        )
    elif not pack_text or not pack_text.strip():
        runs.append(
            CheckRun(
                "warning-wording",
                False,
                "no pack text was supplied, so there was nothing to search. "
                "Pass --pack-text to run it.",
            )
        )
    else:
        produced, not_searched = check_warning_wording(matches, pack_text)
        record("warning-wording", produced)

    return findings, runs, matches, unrestricted, not_searched, considered
