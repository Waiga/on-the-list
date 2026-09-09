"""The shapes this tool reports in.

There is deliberately no verdict type here. No field says compliant, safe,
legal, permitted or clean. Every finding is a statement about two strings: one
printed on the label the user supplied, one printed in an annex to Regulation
(EC) No 1223/2009 as the European Commission publishes it. What follows from
that pairing is a regulatory question, and a regulatory question needs a
regulatory adviser looking at the whole product, not a text comparison.

The one distinction the whole design rests on is between *absent from the
annexes* and *unknown*. The annexes are lists of restricted substances. They
are not an inventory of valid ingredients. Aqua and Glycerin appear in none of
them, and that says nothing about aqua and glycerin except that these five
lists do not restrict them. So there is no ``unrecognised`` field anywhere in
this module. There is ``unrestricted``, and it means exactly what it says.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

#: Which annex an entry came from. Roman numerals, as the Regulation uses.
Annex = Literal["II", "III", "IV", "V", "VI"]

#: Where an ingredient sits on the label. A colourant in a shared "may contain"
#: block is printed across a whole shade range, so it may not be in the unit in
#: the reader's hand, and no positional statement can be made about it.
Position = Literal["declared", "may-contain"]

#: Which column of the annex CSV a name was read from. Reported with every
#: match, because the two columns have different separators and different
#: reliability, and a reader checking a match needs to know which one to open.
NameSource = Literal["glossary", "identified", "colour-index"]


@dataclass(frozen=True)
class Ingredient:
    """One entry parsed out of an ingredient list."""

    #: As printed, minus footnote marks and percentage annotations.
    raw: str
    #: Folded for comparison: casefolded, whitespace collapsed, dashes unified.
    normalised: str
    #: 1-based index within its section, so a finding can say where to look.
    index: int
    position: Position = "declared"
    #: Extra forms this entry was also looked up under, each paired with what
    #: kind of form it is:
    #:
    #:   "whole"  the printed name with a bracketed aside removed, as in
    #:            "Titanium Dioxide (nano)" -> "Titanium Dioxide". Still the
    #:            name of the ingredient.
    #:   "part"   the contents of a bracket, or one side of a spaced slash, as
    #:            in "CI 77288 / CHROMIUM" -> "CHROMIUM". A piece of what is
    #:            printed, which may not be what the entry is about.
    #:
    #: The distinction is load-bearing: a match on a "part" is good enough to
    #: find a colourant inside "Titanium Dioxide (CI 77891)" and is not good
    #: enough to report a substance as prohibited.
    aliases: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AnnexEntry:
    """One row of one annex."""

    annex: Annex
    #: The Commission's own reference number, e.g. "12 a". This is the citation.
    reference: str
    #: Column "Chemical name / INN" (or "Chemical name" in Annex IV).
    chemical_name: str
    #: Every INCI-style name this row carries, as printed in the register.
    names: tuple[str, ...]
    #: Same, folded, paired with the column each came from.
    normalised_names: tuple[tuple[str, NameSource], ...]
    #: Column "Wording of conditions of use and warnings", verbatim. Empty for
    #: every Annex II row, which has no such column at all.
    wording: str = ""
    #: The subset of that wording this tool is willing to look for in pack text.
    #: See annexes.label_phrases for the two rules that produce it.
    label_phrases: tuple[str, ...] = ()
    #: Column "Product Type, body parts" -- reported alongside a match because a
    #: restriction that applies to hair products says nothing about a face cream.
    product_types: str = ""
    update_date: str = ""
    #: The word in the entry's own chemical name that makes the entry
    #: conditional -- "except", "unless", "when used", "other than". Empty when
    #: the entry reads as an unconditional statement about the substance.
    #: Purely lexical: it reports what the Commission wrote, and decides
    #: nothing about whether the condition is met.
    qualifier: str = ""
    #: True when the entry is about the nanomaterial form and none of its own
    #: names says so. Annex II entry 1725 is "Styrene/Acrylates copolymer
    #: (nano)" and lists the plain INCI name "STYRENE/ACRYLATES COPOLYMER"
    #: beside it, so a label printing the ordinary polymer matches an entry
    #: that is not about it.
    nano_only: bool = False

    @property
    def citation(self) -> str:
        return f"Annex {self.annex}, entry {self.reference}"


@dataclass(frozen=True)
class Match:
    """An ingredient on the list, and an annex entry naming it."""

    ingredient: Ingredient
    entry: AnnexEntry
    #: The register's own spelling of the name that matched.
    matched_name: str
    #: Which annex column that spelling came from.
    source: NameSource
    #: Which form of the printed ingredient matched: "as printed", or one of the
    #: alias forms. Named in the report so a reader can judge the match.
    via: str
    #: "as printed", "whole" or "part". See Ingredient.aliases.
    via_kind: str = "as printed"


@dataclass(frozen=True)
class Exclusion:
    """Something the tool matched, considered, and deliberately did not report.

    Printed, so that a reader can tell the difference between "the tool did not
    notice that this product contains Styrene/Acrylates Copolymer, which is in
    Annex II" and "the tool noticed, and the Annex II entry is about the
    nanomaterial form while the label does not say nano". Silence about a
    near-miss reads as an oversight.
    """

    ingredient: Ingredient
    entry: AnnexEntry
    reason: str


@dataclass(frozen=True)
class Finding:
    """One thing the tool observed. Never a verdict."""

    #: Which check produced it: prohibited, colourant-order, repeated-entry,
    #: warning-wording.
    check: str
    #: One line, in the reader's words.
    summary: str
    #: The evidence, one string per line, already in reading order.
    detail: tuple[str, ...] = ()
    #: "Annex II, entry 1329" and the like, where there is one.
    citation: str = ""
    #: True when the annex entry behind this finding carries a condition in its
    #: own wording. Such findings are reported in their own group, after the
    #: unconditional ones, because a condition an ingredient list cannot settle
    #: changes what the finding is worth -- not whether it is printed.
    qualified: bool = False


@dataclass(frozen=True)
class CheckRun:
    """Whether a check ran, and if not, why not.

    Every report lists all of these. A check that did not run must never be
    read as a check that found nothing, and the only way to keep those apart is
    to print both.
    """

    name: str
    ran: bool
    #: Populated when ``ran`` is False. Always a reason, never a blank.
    reason: str = ""
    findings: int = 0


@dataclass(frozen=True)
class RegisterInfo:
    """Which version of the annexes a report was produced against."""

    #: Where the files were read from: "vendored with the package", a cache
    #: path, or a directory the user named.
    origin: str
    #: annex -> (last_update, sha256, data_rows)
    annexes: dict[str, tuple[str, str, int]] = field(default_factory=dict)
    #: Distinct normalised names across all five annexes.
    name_count: int = 0

    def line(self) -> str:
        dates = sorted({value[0] for value in self.annexes.values()})
        stamp = dates[0] if len(dates) == 1 else ", ".join(dates)
        return (
            f"CosIng annexes II-VI, Commission last update {stamp}, "
            f"{self.name_count} distinct names, read from {self.origin}"
        )


@dataclass(frozen=True)
class Report:
    source: str
    ingredients: list[Ingredient]
    #: True when an ingredient list was located and parsed. When False there is
    #: nothing to report and no absence may be claimed.
    parsed: bool
    findings: list[Finding]
    checks: list[CheckRun]
    matches: list[Match]
    register: RegisterInfo
    #: Ingredients no annex entry names. Called unrestricted, never unknown.
    unrestricted: list[Ingredient] = field(default_factory=list)
    #: Matches deliberately not reported as findings, each with its reason.
    considered: list[Exclusion] = field(default_factory=list)
    #: Things that limited what this run could observe, in plain words.
    limits: list[str] = field(default_factory=list)
    #: True when pack text was supplied, which check 4 requires.
    pack_text_supplied: bool = False
