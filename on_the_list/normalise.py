"""Fold a name to the one form both sides of a comparison are written in.

Both sides go through this. That is the point: the label says
``Sodium Benzoate``, the register says ``SODIUM BENZOATE``, and a comparison
that treats those as different names is not a comparison at all.

Everything here is a response to something that appears in one of the two
inputs. The register carries hyphenation and spacing artefacts from the PDF the
Commission typesets the annexes from -- ``ANTHRA- 9,10-QUINONE``, ``MEA-
SALICYLATE`` -- and pack text copied out of a PDF or a web form carries HTML
entities, non-breaking spaces and typographic quotes. Neither is anybody's
fault and both have to be absorbed here or every match is a coin toss.

What this deliberately does **not** do is anything clever. No stemming, no
edit distance, no dropping of words. A fold that maps two genuinely different
substances onto the same string produces a confident false match against a
prohibited-substances list, which is the worst thing this tool could do.
"""

from __future__ import annotations

import html
import re
import unicodedata

# The register writes British forms in places ("selenium disulphide",
# "p-Phenylenediamine Sulphate") while the INCI convention on packs is
# American. Folding both sides the same way is safe; leaving them apart means
# a real entry silently never matches.
_BRITISH = (
    ("sulphate", "sulfate"),
    ("sulphite", "sulfite"),
    ("sulphide", "sulfide"),
    ("sulphur", "sulfur"),
    ("colour", "color"),
    ("aluminium", "aluminum"),
)

# Non-breaking, en/em quad, thin, hair, narrow and ideographic spaces, plus the
# zero-width space. All of these arrive in text copied out of a PDF or pasted
# through a web form, and each one breaks a comparison silently.
_SPACES = re.compile(r"[  -​  　]")
# Every dash Unicode offers, plus the soft hyphen, folded to the ASCII one.
_DASHES = re.compile(r"[‐-―−­]")
_WHITESPACE = re.compile(r"\s+")
_AROUND_HYPHEN = re.compile(r"\s*-\s*")

#: ``CI 12345`` in any of the ways a pack or the register writes it, plus the
#: one way a scanner writes it. ``Cl 77492`` with a lowercase L is endemic in
#: OCR'd panels -- it appears beside a correctly read ``CI`` in the same list --
#: and reading it as an ordinary ingredient makes a colourant look like a
#: non-colourant sitting after one, which is the position check's commonest
#: false alarm. No cosmetic ingredient is named "Cl" followed by five digits.
COLOUR_INDEX = re.compile(r"^c\.?\s?[il]\.?\s*(\d{5}(?::\d{1,2})?)$")


def fold(name: str) -> str:
    """Return the comparison form of ``name``.

    Idempotent: ``fold(fold(x)) == fold(x)`` for every string, which the tests
    check over the whole register rather than over a handful of examples.
    """
    text = html.unescape(name)
    text = unicodedata.normalize("NFKC", text)
    text = _SPACES.sub(" ", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = _DASHES.sub("-", text)
    # A hyphen with a space beside it is a line break the typesetter put there,
    # not part of the name. "ANTHRA- 9,10-QUINONE" and "MEA- SALICYLATE" are
    # both in the register exactly like that.
    text = _AROUND_HYPHEN.sub("-", text)
    text = text.casefold()
    for british, american in _BRITISH:
        text = text.replace(british, american)
    text = _WHITESPACE.sub(" ", text).strip()
    text = text.strip(" .,;:")
    match = COLOUR_INDEX.match(text)
    if match:
        # "C.I. 77491", "CI77491" and "ci 77491" are the same colourant, and
        # the register writes it "CI 77491". One spelling wins.
        return f"ci {match.group(1)}"
    return text


def is_colour_index(folded: str) -> bool:
    """Whether a folded name is a bare colour index number.

    Deliberately narrow. ``Titanium Dioxide`` is in Annex IV and is also a UV
    filter and an opacifier, so its presence proves nothing about what it is
    doing in a formula. ``CI 77891`` is unambiguous, and the position check is
    restricted to that form for exactly that reason.
    """
    return bool(re.fullmatch(r"ci \d{5}(?::\d{1,2})?", folded))
