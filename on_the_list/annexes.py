"""Read the Commission's annex CSVs into entries.

The files are a CSV rendering of a legal text that is typeset as a PDF, and it
shows. There is a four-line preamble before the real header. Two different
columns hold ingredient names and they use two different separators. Chemical
names contain commas, so the column that *is* comma-separated cannot simply be
split on commas. Names carry line-break hyphenation from the PDF layout.

None of that is a complaint. It is the shape of the input, and getting it wrong
does not produce an error, it produces a register full of fragments that then
quietly match nothing. Every rule below exists because a simpler rule shredded
a real name.
"""

from __future__ import annotations

import csv
import io
import re

from on_the_list.models import AnnexEntry, NameSource
from on_the_list.normalise import fold

#: Row 4 of every annex CSV is the real column header. Rows 0-3 are the file
#: creation date, the annex number and its last-update date, the title of the
#: annex, and a spanning group header.
HEADER_ROW = 4

#: The columns that hold INCI-style names, and the separator each uses.
#:
#: These are two genuinely different columns with two genuinely different
#: conventions, and the difference is the single most important fact about
#: parsing these files.
GLOSSARY_COLUMNS = (
    "Name of Common Ingredients Glossary",
    "Colour index Number / Name of Common Ingredients Glossary",
)
IDENTIFIED_COLUMN = "Identified INGREDIENTS or substances e.g."
WORDING_COLUMN = "Wording of conditions of use and warnings"
PRODUCT_TYPE_COLUMN = "Product Type, body parts"

#: The glossary columns separate names with ``;`` or ``/`` and never with a
#: comma. Splitting them on commas turns
#: ``1-HEXYL 4,5-DIAMINO PYRAZOLE SULFATE`` into ``1-HEXYL 4`` and
#: ``5-DIAMINO PYRAZOLE SULFATE``, neither of which is a substance.
_GLOSSARY_SEPARATOR = re.compile(r"[;/]")

#: Placeholders the Commission uses for "this row has no glossary name".
_EMPTY = frozenset({"", "-", "--", "n/a", "na"})

#: The words chemistry uses as locants and stereodescriptors, which are spelled
#: out rather than numbered. They sit in front of a comma exactly as a digit
#: does: "alpha,alpha-Dimethylbenzyl Alcohol", "trans,trans-Dibenzylideneacetone".
#: This is a convention, not a list fitted to a corpus, and it is closed.
_WORD_LOCANTS = (
    "alpha|beta|gamma|delta|epsilon|omega|cis|trans|syn|anti|endo|exo|"
    "ortho|meta|para|sym|tert|sec|iso|neo|erythro|threo"
)

#: A fragment that is a locant rather than a name: a position number, a prime,
#: one of the single letters chemistry uses for a substitution point, or one of
#: the words above. Used to decide whether a comma is a separator or part of a
#: name -- see ``split_identified``.
_LOCANT_TAIL = re.compile(r"(?:\d|')$")
_LOCANT_PIECE = re.compile(r"(?i)^(?:[A-Za-z]'?|\d{1,2}'?|" + _WORD_LOCANTS + r")$")
#: A fragment that begins as a numeric or single-letter locant continues.
_LOCANT_HEAD = re.compile(r"^(?:\d|[A-Za-z]'?[-,])")
#: The same, for the spelled-out locants. Kept separate because it may only
#: follow another spelled-out locant: allowing it after any digit merged
#: "CI 40800,beta-Carotene", two names, into one that is neither.
_WORD_LOCANT_HEAD = re.compile(r"(?i)^(?:" + _WORD_LOCANTS + r")[-,]")


def _is_locant_run(fragment: str) -> bool:
    """Whether every comma-separated piece of ``fragment`` is a locant.

    "N", "1,2" and "alpha,alpha" are; "1,3-BIS-(2" and "HCl" are not. Without
    this, a third locant broke the merge: "N,N,N-TRIMETHYLGLYCINE,AQUA" split
    after the second comma and put a substance called "N" in the register --
    the exact failure the merge exists to prevent, one locant further along.
    """
    fragment = fragment.strip()
    if not fragment:
        return False
    return all(_LOCANT_PIECE.match(piece) for piece in fragment.split(","))


def split_glossary(value: str) -> list[str]:
    """Split a glossary or colour-index cell into names.

    On ``;`` and ``/`` only. Never on a comma.
    """
    out = []
    for part in _GLOSSARY_SEPARATOR.split(value):
        part = part.strip()
        if part.lower() not in _EMPTY:
            out.append(part)
    return out


def split_identified(value: str) -> list[str]:
    """Split the "Identified INGREDIENTS" cell into names.

    This column *is* comma-separated. The difficulty is that a great many
    chemical names contain a comma of their own::

        1,3-Bis(hydroxymethyl)-3-thiourea
        N,N-DIETHYL-m-AMINOPHENOL
        4,4'-ISOPROPYLIDENEDIPHENOL
        PEG-3,2',2'-Di-p-PHENYLENEDIAMINE

    A plain ``value.split(",")`` turns the second of those into ``N`` and
    ``N-DIETHYL-m-AMINOPHENOL``, and the register then contains a "substance"
    called ``N``. In the September 2026 files that happens on 40 rows.

    The rule here is that a comma is **part of a name** when the fragment
    before it ends in a locant -- a digit, a prime, or a lone letter -- *and*
    the fragment after it starts like a locant continuation. Both halves are
    needed. ``CI 77480,GOLD`` ends in a digit and is still a real separator;
    ``DICHLOROMETHANE,4,6-DIMETHYL-PYRAN-2-ONE`` starts with a digit after the
    first comma and is also a real separator. Requiring both conditions gets
    every case in the current files right, and the tests carry all of them.

    This is a heuristic over a column the Commission does not document, and it
    is written down in the README as one. A name it splits wrongly becomes a
    fragment that matches nothing, so the failure mode is a missed match rather
    than a false one.
    """
    if not value.strip():
        return []
    fragments = value.split(",")
    merged: list[str] = [fragments[0]]
    for fragment in fragments[1:]:
        previous = merged[-1].rstrip()
        # Two ways a comma can belong to a name. Either the fragment before it
        # ends in a digit or a prime and the one after starts as a locant --
        # "PEG-3,2',2'-Di-p-PHENYLENEDIAMINE". Or the fragment before it is
        # itself nothing but locants, in which case a spelled-out locant may
        # follow too, and so may a bare one: splitting
        # "N,N,N-TRIMETHYLGLYCINE" leaves an "N" in the middle with no hyphen
        # after it, because the comma went to the split.
        run = _is_locant_run(previous)
        joins = _LOCANT_HEAD.match(fragment) or (
            run
            and (_WORD_LOCANT_HEAD.match(fragment) or _is_locant_run(fragment))
        )
        if (_LOCANT_TAIL.search(previous) or run) and joins:
            merged[-1] = merged[-1] + "," + fragment
        else:
            merged.append(fragment)
    out = []
    for part in merged:
        part = part.strip()
        if part.lower() not in _EMPTY:
            out.append(part)
    return out


#: A mandatory statement of the ``Contains X`` form, at the start of a line, or
#: after a short qualifier ending in a colon on that same line -- the annexes
#: write both ``Contains thioglycolate`` and ``Above 2%: Contains ammonia``.
#:
#: This is the *only* shape of wording this tool will look for in pack text, and
#: the narrowness is the whole reason the warning check is worth running. The
#: wording column mixes two unrelated things: text that must be printed on the
#: label ("Contains thioglycolate"), and conditions that are nothing to do with
#: the label at all ("Purity criteria as set out in Commission Directive
#: 95/45/EC (E 129)", "Only nanomaterials having the following characteristics
#: are allowed"). Treating the whole column as label text would report a missing
#: warning for every sunscreen containing zinc oxide, which is nonsense.
#:
#: An earlier version also pulled out quoted passages, since the annexes quote
#: the long hair-dye warnings. It was abandoned: the annexes use apostrophes as
#: quotation marks, the quoted text contains apostrophes and inner quotes around
#: "black henna", and the extractor produced fragments like ``tattoo in the
#: past``. A rule that yields garbage on the inputs it was written for is not a
#: rule. Those long warnings are therefore reported as attached-but-not-checked.
#: The qualifier is capped at 60 characters and must be on the same line, so
#: this cannot reach backwards across a paragraph. Over the September 2026
#: files it adds exactly two statements to the thirty-three the bare line-start
#: rule finds -- "Contains Benzophenone-3" and "Contains ammonia" -- and it
#: lengthens none of the others.
_CONTAINS = re.compile(
    r"(?im)^(?:[^\n:]{0,60}:[ \t]*)?[\s\"'‘’“”(]*?(contains\b[^\n.;]{2,140})"
)
_FOOTNOTE_TAIL = re.compile(r"\s*\((?:\*+|\d{1,2})\)\s*$")


def label_phrases(wording: str) -> tuple[str, ...]:
    """The subset of a wording cell this tool will look for in pack text.

    Returns the ``Contains ...`` statements and nothing else. Everything the
    cell also says is reported to the reader verbatim, uninterpreted.
    """
    found = []
    for match in _CONTAINS.finditer(wording):
        phrase = _FOOTNOTE_TAIL.sub("", match.group(1).strip())
        if phrase and phrase not in found:
            found.append(phrase)
    return tuple(found)


#: Words that make an annex entry's own statement conditional.
#:
#: This is a lexical read of the Commission's text and nothing more. It does
#: not decide whether a condition is met -- an ingredient list cannot settle
#: "except if the full refining history is known", "when used as a substance in
#: hair dye products" or "other than". It only lets the report put the entries
#: that say something unconditional about a substance ahead of the entries that
#: do not, instead of printing them as though they carried equal weight.
#:
#: Over the September 2026 Annex II these words fire on the entries behind
#: roughly two thirds of the matches found in a 16,635-label corpus: petrolatum
#: (refining history), the hair-dye-only colourants, and the furocoumarin entry
#: that names ordinary citrus oils "except for normal content in natural
#: essences used". A bare "if" counts too. 333 Annex II entries carry one, and
#: every one of them is a condition on composition that a name on a label cannot
#: settle: 149 read "if it contains > 0,1 % w/w Butadiene", and the rest name a
#: different impurity -- "Pitch, coal tar-petroleum, if it contains > 0.005 %
#: w/w benzo[a]pyrene" is entry 613.
_QUALIFIER = re.compile(
    r"(?i)\b(except(?:\s+if| for| where)?|unless|when used|other than|"
    r"with the exception of|only (?:if|when)|provided that|if)\b"
)

#: An entry about the nanomaterial form.
_NANO = re.compile(r"(?i)\(\s*nano\s*\)|\bnanomaterial\b|\bnanoparticle")


def qualifier_in(chemical_name: str) -> str:
    """The conditional phrase in an entry's own name, or "" if it reads flatly."""
    match = _QUALIFIER.search(chemical_name)
    return match.group(0) if match else ""


def is_nano_only(chemical_name: str, names: tuple[str, ...]) -> bool:
    """Whether an entry is about a nano form its own INCI names do not mark.

    Annex II entry 1725 is "Styrene/Acrylates copolymer (nano)" and its
    identified-ingredients column reads "STYRENE/ACRYLATES COPOLYMER" with no
    nano marker at all. A label printing the ordinary polymer therefore matches
    an entry that is not about the ordinary polymer -- 421 times in a
    16,635-label corpus, the second commonest match in it. That is a defect in
    the comparison, not a finding about those products.
    """
    if not _NANO.search(chemical_name):
        return False
    return not any(_NANO.search(name) for name in names)


def read_annex(annex: str, text: str) -> list[AnnexEntry]:
    """Parse one annex CSV into entries, in file order."""
    # io.StringIO, never text.splitlines(). A quoted CSV field may contain
    # newlines, and the annexes use them heavily -- a wording cell is often ten
    # lines of conditions. Feeding csv.reader a list of lines silently glues
    # those lines together with nothing between them, which turned
    # "Contains selenium disulphide\nAvoid contact with eyes" into
    # "Contains selenium disulphideAvoid contact with eyes" and made six of the
    # thirty extractable warning phrases run on into the sentence after them.
    # The reader reported no error and the tests were green.
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) <= HEADER_ROW:
        raise ValueError(f"Annex {annex}: file is too short to hold a header")
    header = rows[HEADER_ROW]
    if "Reference Number" not in header:
        raise ValueError(
            f"Annex {annex}: row {HEADER_ROW} is not the column header. "
            "The Commission may have changed the export format."
        )
    glossary_column = next((c for c in GLOSSARY_COLUMNS if c in header), None)

    entries: list[AnnexEntry] = []
    for raw in rows[HEADER_ROW + 1 :]:
        if not any(cell.strip() for cell in raw):
            continue
        row = dict(zip(header, raw))
        pairs: list[tuple[str, NameSource]] = []
        if glossary_column:
            source: NameSource = (
                "colour-index"
                if glossary_column.startswith("Colour index")
                else "glossary"
            )
            for name in split_glossary(row.get(glossary_column, "")):
                pairs.append((name, source))
        for name in split_identified(row.get(IDENTIFIED_COLUMN, "")):
            pairs.append((name, "identified"))

        seen: dict[str, tuple[str, NameSource]] = {}
        for name, source in pairs:
            key = fold(name)
            if key and key not in seen:
                seen[key] = (name, source)

        wording = row.get(WORDING_COLUMN, "") or ""
        chemical = (
            row.get("Chemical name / INN") or row.get("Chemical name") or ""
        ).strip()
        entries.append(
            AnnexEntry(
                annex=annex,  # type: ignore[arg-type]
                reference=(row.get("Reference Number", "") or "").strip(),
                chemical_name=chemical,
                names=tuple(name for name, _ in seen.values()),
                normalised_names=tuple(
                    (key, source) for key, (_, source) in seen.items()
                ),
                wording=wording.strip(),
                label_phrases=label_phrases(wording),
                product_types=(row.get(PRODUCT_TYPE_COLUMN, "") or "").strip(),
                update_date=(row.get("Update Date", "") or "").strip(),
                qualifier=qualifier_in(chemical),
                nano_only=is_nano_only(chemical, tuple(n for n, _ in seen.values())),
            )
        )
    return entries


def read_header_dates(text: str) -> tuple[str, str]:
    """Return (file creation date, Commission last-update date) from rows 0-1.

    These are what a report cites when it names the register version it used.
    """
    rows = list(csv.reader(io.StringIO(text)))[:2]
    creation = ""
    update = ""
    if rows and rows[0]:
        creation = rows[0][0].partition(":")[2].strip()
    if len(rows) > 1 and len(rows[1]) > 1:
        update = rows[1][1].partition(":")[2].strip()
    return creation, update
