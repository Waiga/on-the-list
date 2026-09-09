"""Find and parse the ingredient list inside a block of label text.

Printed INCI lists are not tidy. They arrive with the preamble in six
languages, colourants in a shared "may contain" block, supplier blend notation
in the middle of a name, footnote asterisks pointing at an organic-content
claim, and commas inside parentheses that must not be split on.

The parsing approach here started from the equivalent module in
``says-on-the-tin``, a sibling tool, and was cut down: that one has to keep
marketing prose apart from ingredients, and this one does not care about
marketing prose at all.
"""

from __future__ import annotations

import html
import re

from on_the_list.models import Ingredient, Position
from on_the_list.normalise import fold

# The word that introduces the list, in the languages that share a European
# pack, plus the two abbreviations used on specification sheets.
_PREAMBLE = re.compile(
    r"(?im)^\W{0,4}(?:"
    r"ingredients?|ingr[ée]dients?|inhaltsstoffe|zutaten|ingredienti|"
    r"ingredientes|ingredi[eë]nten|composition|sk[lł]adniki|"
    r"st[oa]f[fn]er|ainesosat|inci"
    r")\b\s*[:\-–]?\s*"
)

#: Every panel heading that can follow an ingredient list on a pack, in the
#: languages a European pack is printed in. The non-English forms are not
#: decoration: an English-only terminator read "Précautions: éviter le contact
#: avec les yeux" as an ingredient, on a pack that also printed the list in
#: English. The same list is reused to decide that a colon-terminated heading
#: is a pack panel rather than a second product's component.
_PANEL_WORDS = (
    r"directions?|how\s+to\s+use|usage|application|warnings?|caution|"
    r"precautions?|storage|store\s+in|net\s+(?:wt|weight|vol)|"
    r"manufactured\s+(?:by|for)|marketed\s+by|distributed\s+by|made\s+in|"
    r"best\s+before|expiry|use\s+by|customer\s+care|for\s+external\s+use|"
    r"keep\s+out\s+of\s+reach|uses?|purpose|active\s+ingredients?|"
    r"inactive\s+ingredients?|other\s+information|"
    # French
    r"pr[ée]cautions?|mode\s+d.emploi|conseils?\s+d.utilisation|utilisation|"
    r"attention|fabriqu[ée]\s+(?:par|en)|distribu[ée]\s+par|contenance|"
    # Spanish and Portuguese
    r"precauciones|modo\s+de\s+(?:uso|empleo|usar)|advertencias?|"
    r"conservaci[óo]n|fabricado\s+por|pa[íi]s\s+de\s+origen|"
    r"advert[êe]ncias?|conserva[çc][ãa]o|"
    # German, Italian, Dutch, Nordic
    r"anwendung|hinweise?|warnhinweise?|aufbewahr\w*|"
    r"hergestellt\s+(?:von|f[üu]r)|modo\s+d.uso|avvertenze|conservare|"
    r"prodotto\s+da|gebruiksaanwijzing|waarschuwing\w*|bewaren|"
    r"bruksanvisning|advarsel|oppbevar\w*"
)

_TERMINATOR = re.compile(r"(?im)^\W{0,4}(?:" + _PANEL_WORDS + r")\b")

# The same panels when they run on inline rather than starting a line.
#
# The second alternative is the content declaration a toothpaste must print:
# "Contient du fluorure de sodium (1450 ppm de fluor)", "inneholder:
# natriumfluorid (1450ppm F)", "Contains: Sodium Fluoride 0,32% w/w". It sits
# immediately after the colourants at the end of the list, with no line break,
# and reading it as an ingredient was the single commonest reason a colourant
# appeared to be printed in front of a non-colourant -- seven of the ten wrong
# position findings in a hand-audited sample of thirty. It is recognised by the
# concentration it carries, not by the word "contains" alone, so an ingredient
# list that happens to use that word is untouched.
_INLINE_TERMINATOR = re.compile(
    # A panel heading with a colon after it, run on from the list rather than
    # starting a line: "..., Glycerin. Modo de uso: aplicar". The colon is
    # required, because several of the panel words -- usage, application,
    # purpose, attention -- are ordinary enough that matching them bare would
    # cut a list short.
    r"(?i)(?:^|[.;\n])\s*(?:" + _PANEL_WORDS + r")\s*:"
    r"|\b(?:if\s+swallowed|if\s+in\s+eyes|avoid\s+contact\s+with\s+"
    r"(?:the\s+)?eyes|call\s+a?\s*poison|seek\s+medical|discontinue\s+use|"
    r"keep\s+out\s+of\s+reach|for\s+external\s+use\s+only)\b"
    # The content declaration must start a sentence or carry a colon. Matching
    # it anywhere cut "Aqua, Glycerin, Contains Nothing Extract 2%, Butylphenyl
    # Methylpropional" down to two ingredients and lost the prohibited match
    # after it.
    r"|(?:^|[.\n]|:)\s*(?:contains?|contient|cont[eé]m|contiene|contien[ei]|"
    r"inneholder|indeholder|enth[äa]lt|inneh[åa]ller|sis[äa]lt[äa][äa])\b"
    r"[^.\n]{0,90}?\d[\d.,]*\s*(?:ppm|%|mg)"
)

# The colourant block. One list is printed across a whole shade range, so
# anything after this marker may not be in the unit in the reader's hand. The
# position check therefore never looks at it.
#: ``[+/- CI 77491, CI 77492]`` is the commonest printed form, and the closing
#: bracket comes after the colourants rather than after the marker. A pattern
#: that required ``[+/-]`` as a unit matched none of it, so a whole shade-range
#: block was read as declared ingredients and the position check then had a
#: dozen colourants to be confused by.
_MARKER = r"(?:\+\s*/\s*-|\+/-|±)"
_MAY_CONTAIN_WORDS = (
    r"may\s+contain|peut\s+contenir|kann\s+enthalten|puede\s+contener|"
    r"pu[òo]\s+contenere|pode\s+conter"
)
#: A bare marker only opens a shade-range block when it is bracketed, or the
#: words follow it, or a colour index number does. "Glycerin +/- 0.5%" and
#: "pH 5.5 +/- 0.5" are ordinary label text, and reading either as the start of
#: a shade-range block moved every declared ingredient after it out of both
#: order-dependent checks while telling the reader only that the list "has a
#: 'may contain' block".
_MAY_CONTAIN = re.compile(
    r"(?i)[\[(]\s*" + _MARKER + r"\s*[\])]?\s*"
    r"(?:\b(?:" + _MAY_CONTAIN_WORDS + r")\b\s*[:\-]?\s*)?"
    r"|" + _MARKER + r"\s*(?=\s*c\.?\s?[il]\.?\s*\d{5})"
    r"|" + _MARKER + r"\s*(?:\b(?:" + _MAY_CONTAIN_WORDS + r")\b\s*[:\-]?\s*)"
    r"|\b(?:" + _MAY_CONTAIN_WORDS + r")\b\s*[:\-]?\s*"
)

# Supplier blend notation: "Ingredient A (and) Ingredient B" is two things.
_BLEND = re.compile(r"(?i)\s*\((?:and|et|und)\)\s*")

# Percentage and footnote annotations that ride along with a name.
_ANNOTATION = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s*%(?:\s*(?:min|max|w/w|v/v))?\.?)"
    r"|(?:\b(?:min|max|approx\.?)\s*\d+(?:[.,]\d+)?\s*%)"
    # A tolerance printed against a quantity: "Glycerin +/- 0.5%". Without
    # this the percentage went and the "+/-" stayed on the name.
    r"|(?:\s*(?:\+\s*/\s*-|\+/-|±)\s*(?=\s*\d|\s*$))"
)
_FOOTNOTE = re.compile(r"[*†‡°^•·]+")

# Punctuation or numbering rather than an ingredient.
_NOT_AN_INGREDIENT = re.compile(r"^[\W_]*$")

_PARENTHETICAL = re.compile(r"\(([^()]{1,80})\)")
#: Whitespace on BOTH sides. The printed convention for two names of one thing
#: is "AQUA / WATER" and "CI 77891 / TITANIUM DIOXIDE". Accepting a space on
#: one side only split "STYRENE/ ACRYLATES COPOLYMER" -- a typesetting artefact,
#: not a synonym -- into two ingredients, and the fragment "STYRENE" then
#: matched Annex II entry 1575, the styrene monomer, on 35 real labels.
_SYNONYM_SLASH = re.compile(r"\s+/\s+")

#: A polymer name whose slashes list monomers rather than synonyms. This is an
#: INCI naming convention, not a guess: "Styrene / Acrylates Copolymer",
#: "Acrylates / C10-30 Alkyl Acrylate Crosspolymer", "VP / VA Copolymer". The
#: slashes are spaced exactly like a synonym list, and splitting them left the
#: fragment "Styrene", which matches the styrene monomer in Annex II, on 21
#: real labels.
_POLYMER = re.compile(r"(?i)\b(?:co|cross|homo)?polymer\b\s*$")


def extract(text: str) -> tuple[str, bool]:
    """Split label text into (the ingredient block, whether one was found).

    When there is no preamble, nothing is returned and the caller is told so.
    Guessing is worse than admitting it: a run that treats a paragraph of
    marketing copy as an ingredient list produces confident nonsense. The
    caller has ``--ingredients`` for saying "this file *is* the list".
    """
    match = _PREAMBLE.search(text)
    if match is None:
        return "", False

    block, _ = trim(text[match.end() :])
    if not block.strip():
        return "", False
    return block, True


def trim(block: str) -> tuple[str, str]:
    """Cut a block at the first thing that is a pack panel rather than a list.

    Returns the block and the text that was cut, so the caller can say what it
    dropped instead of dropping it quietly. Used on both paths: a block handed
    straight to ``--ingredients`` needs this exactly as much as one found
    inside a whole label does, and for a while only the second one got it.

    A leading "Ingredients:" is removed here too. A file handed to
    ``--ingredients`` is very often copied straight off a pack and starts with
    the word, and without this the first ingredient became "Ingredients:
    Formaldehyde", matched nothing, and the run exited 0. The same text through
    the whole-label path reported the prohibited match. Same file, opposite
    answer, no warning.
    """
    preamble = _PREAMBLE.match(block.lstrip())
    if preamble is not None:
        block = block.lstrip()[preamble.end() :]
    end = _TERMINATOR.search(block)
    inline = _INLINE_TERMINATOR.search(block)
    if inline is not None and (end is None or inline.start() < end.start()):
        end = inline
    if end is None:
        return block, ""
    return block[: end.start()], block[end.start() :]


def _split_top_level(block: str) -> list[str]:
    """Split on separators that are not inside brackets.

    ``Butyrospermum Parkii (Shea, Karite) Butter`` is one ingredient, and the
    comma inside the parentheses must not end it.
    """
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in block:
        if char in "([{":
            depth += 1
            buf.append(char)
        elif char in ")]}":
            depth = max(0, depth - 1)
            buf.append(char)
        elif depth == 0 and (char in ",;\n\r" or char in "•·‣|"):
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    parts.append("".join(buf))
    return parts


def split_sections(block: str) -> list[tuple[str, Position]]:
    """Split a block into declared and 'may contain' sections, in order.

    When the marker opened a bracket -- ``[+/- CI 77491, CI 77492] Talc`` --
    the shade-range section ends at the matching closing bracket, and anything
    after it is declared again. Treating the rest of the block as shade-range
    would move real declared ingredients out of the position check, which is a
    quieter mistake than the one it replaced and just as wrong.
    """
    sections: list[tuple[str, Position]] = []
    cursor = 0
    for match in _MAY_CONTAIN.finditer(block):
        if match.start() < cursor:
            continue
        sections.append((block[cursor : match.start()], "declared"))
        opener = match.group(0).lstrip()[:1]
        end = len(block)
        if opener in "[(":
            closer = {"[": "]", "(": ")"}[opener]
            found = block.find(closer, match.end())
            if found != -1:
                end = found
        sections.append((block[match.end() : end], "may-contain"))
        cursor = end + 1 if end < len(block) else len(block)
    sections.append((block[cursor:], "declared"))
    return [(text, kind) for text, kind in sections if text.strip()]


def _clean(token: str) -> str:
    token = _ANNOTATION.sub(" ", token)
    token = _FOOTNOTE.sub(" ", token)
    token = re.sub(r"\s+", " ", token).strip()
    token = token.strip(" .,;:-")
    # A bracket left over from a block marker whose opening half was consumed,
    # as in the last entry of "[+/- CI 77491, CI 77492]". Only an unbalanced
    # one is removed: "Aqua (Water)" ends with a bracket that belongs to it.
    while token and token[-1] in ")]}" and token.count(token[-1]) > token.count(
        {")": "(", "]": "[", "}": "{"}[token[-1]]
    ):
        token = token[:-1].rstrip(" .,;:-")
    return token


def _aliases(raw: str) -> tuple[tuple[str, str], ...]:
    """Other forms of a printed name worth looking up.

    Packs print ``Titanium Dioxide (CI 77891)``, ``Aqua (Water/Eau)`` and
    ``Butyrospermum Parkii (Shea) Butter``. The register holds ``CI 77891`` on
    its own, so the parenthetical has to be looked up separately or the most
    common way a colourant is printed never matches anything.

    Both the whole string with its brackets removed and the contents of each
    bracket are tried. Every match records which of these forms produced it,
    so a reader can see whether a finding rests on the name as printed or on a
    fragment of it.
    """
    forms: list[tuple[str, str]] = []
    # Folded once. Recomputing it inside the loop made a single entry holding
    # 3,000 slash-separated names take 2.4 seconds, because every comparison
    # re-folded the whole 24,000-character string.
    folded_raw = fold(raw)
    # The printed name with a bracketed aside taken off. Still the name of the
    # ingredient, so a match on it is a match on the ingredient.
    stripped = _PARENTHETICAL.sub(" ", raw)
    stripped = re.sub(r"\s+", " ", stripped).strip(" .,;:-")
    if stripped and fold(stripped) != folded_raw:
        # Whether what is left is still the name depends on how much of the
        # name it is. "Citrus Limon (Lemon) Peel Oil" keeps four words of five
        # and is the INCI name; "Styrene (Acrylate Copolymer)" keeps one of
        # three and is a fragment that matched the styrene monomer in Annex II.
        # The rule is that the part outside the brackets must be at least half
        # the words. It is the same test either way round, so "Chromium (CI
        # 77288)" and "CI 77288 / CHROMIUM" now get the same answer; before,
        # one was reported as prohibited and the other was not.
        outside = len(stripped.split())
        inside = sum(len(inner.split()) for inner in _PARENTHETICAL.findall(raw))
        forms.append((stripped, "whole" if outside >= inside else "part"))
    # "CI 77891 / TITANIUM DIOXIDE" and "AQUA / WATER / EAU" are one entry
    # printed under two or three names. A slash with a space on both sides is
    # that convention; a slash without one is part of a single name, as in
    # "Caprylic/Capric Triglyceride". A polymer is the exception: its slashes
    # list monomers, and the test for one ignores a trailing bracket because
    # packs print "Styrene / Acrylates Copolymer (F.I.L. C183943/1)".
    slashed = [] if _POLYMER.search(stripped or raw) else _SYNONYM_SLASH.split(raw)
    for piece in slashed:
        piece = piece.strip(" .,;:-")
        if piece and fold(piece) != folded_raw:
            forms.append((piece, "part"))
    for inner in _PARENTHETICAL.findall(raw):
        for piece in re.split(r"[/,]", inner):
            piece = piece.strip()
            if piece and fold(piece) != folded_raw:
                forms.append((piece, "part"))
    seen: list[tuple[str, str]] = []
    taken: set[str] = set()
    for form, kind in forms:
        key = fold(form)
        if key and key not in taken:
            taken.add(key)
            seen.append((form, kind))
    return tuple(seen)


#: An entry with more words than any INCI name has. The longest in the register
#: is under eight; a token above that is a sentence of pack prose that ended up
#: inside the panel. They are kept and reported, never silently dropped, but
#: their presence is worth telling the reader about: it means the input is not
#: a clean ingredient list, and every count in the report is affected.
_PROSE_WORDS = 8


#: A short heading followed by a colon and then a list -- "Gel N°1:", "Color
#: Gel:", "MASQUE:", "Blonderingscreme:". A multi-component pack declares one
#: list per component in a single field, and the two order-dependent checks
#: cannot be run on it: an ingredient repeated once in each component is not a
#: repeated ingredient, and a colourant at the end of the first list sits in
#: front of the whole of the second.
#:
#: This was measured, not guessed. Of 30 hand-audited duplicate findings on
#: labels with no prose contamination, 12 were multi-component packs and every
#: one was wrong. None of the 11 sound findings in the same sample carried a
#: component heading.
_HEADING = re.compile(
    r"(?:^|[,.;•·\n]|\)\s)\s*([#A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 °/'’#\-]{1,38}?)\s*:\s"
)

#: Headings that introduce the one list, or a panel that is not a list at all.
#: Without this filter the commonest "component heading" in a 16,635-label
#: corpus is the word "Ingredients", which is not one.
_NOT_A_COMPONENT = re.compile(
    r"(?i)^(?:"
    r"ingredients?|ingr[ée]dients?|ingredientes?|ingredienti|inhaltsstoffe|"
    r"weitere\s+inhaltsstoffe|zutaten|ingredi[eë]nten|composition|composicion|"
    r"sk[lł]adniki|st[oa]f[fn]er|ainesosat|inci|sastojci|ingrediente|"
    r"contains?|contient|cont[ée]m|contiene|enth[äa]lt|inneholder|indeholder|"
    r"may\s+contain|peut\s+contenir|kann\s+enthalten|puede\s+contener|"
    r"first\s+aid\s+treatment|ph|code\s+fil|fil\s+code|"
    + _PANEL_WORDS +
    r")(?:\s*[/·].*)?$"
)


def component_headings(block: str) -> list[str]:
    """Component labels found in an ingredient field, deduplicated.

    An empty result means the field reads as one product's list.

    A second "Ingredients:" counts as a component label even though the first
    one does not. One is the heading of the list; two are two lists.
    """
    found: list[str] = []
    preambles: list[str] = []
    for match in _HEADING.finditer(html.unescape(block)):
        heading = match.group(1).strip()
        if _NOT_A_COMPONENT.match(heading):
            preambles.append(heading)
            continue
        if heading.lower() not in [h.lower() for h in found]:
            found.append(heading)
    if len(preambles) > 1 and not found:
        found.append(f"{preambles[0]} (appearing {len(preambles)} times)")
    return found


def looks_like_prose(item: Ingredient) -> bool:
    return len(item.raw.split()) > _PROSE_WORDS


def parse(block: str) -> list[Ingredient]:
    """Turn an ingredient block into ingredients, in printed order.

    HTML entities are resolved **before** splitting. Resolving them afterwards
    left ``&lt;`` and ``&amp;`` split down the middle by the ``;``, so that a
    Russian pack listing "&lt; 5 %" three times produced three ingredients
    called ``&lt``, and an American one produced three called ``FD``, each
    reported as a repeated ingredient. Real records, both of them.
    """
    block = html.unescape(block)
    sections = split_sections(block)

    out: list[Ingredient] = []
    # One running index per kind of section, so that a declared entry printed
    # after a shade-range block continues the declared numbering instead of
    # restarting it. The number is what a reader uses to find the entry.
    indices: dict[str, int] = {"declared": 0, "may-contain": 0}
    for section, position in sections:
        for chunk in _split_top_level(section):
            for piece in _BLEND.split(chunk):
                raw = _clean(piece)
                if not raw or _NOT_AN_INGREDIENT.match(raw):
                    continue
                folded = fold(raw)
                if not folded:
                    continue
                indices[position] += 1
                out.append(
                    Ingredient(
                        raw=raw,
                        normalised=folded,
                        index=indices[position],
                        position=position,
                        aliases=_aliases(raw),
                    )
                )
    return out


def looks_binary(text: str) -> bool:
    """Whether a block is bytes rather than a printed ingredient list.

    Taken from ``says-on-the-tin``, where a binary file appended after an
    ``Ingredients:`` heading parsed into junk tokens, matched nothing, and was
    reported as a clean result -- the most reassuring thing a checker can say,
    about a file it never read.
    """
    sample = text[:4000]
    if not sample:
        return False
    if "\x00" in sample:
        return True
    # U+FFFD counts against it. The file is read with errors="replace", so a
    # non-UTF-8 binary with no NUL bytes arrives as a wall of replacement
    # characters -- and str.isprintable() says every one of them is printable,
    # so the old test called it a list and parsed ingredients out of it.
    printable = sum(
        1
        for ch in sample
        if (ch.isprintable() or ch in "\t\n\r") and ch != "\ufffd"
    )
    return printable / len(sample) < 0.85
