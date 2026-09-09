"""What is in ``on_the_list/data``, where it came from, and its exact bytes.

This module is the reproducibility contract. It is Python source rather than a
JSON file on purpose: the test that checks the package holds nothing but source
and declared data has to be able to read the declaration itself.

Every hash here is of the file exactly as the European Commission's API served
it. Nothing is reformatted, filtered or corrected on the way in, so anyone can
re-run::

    curl -s https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/V/export-csv \\
      | shasum -a 256

and compare. The Commission updates the annexes; when they do, the hash will
stop matching, and that is the point. A register whose version cannot be named
cannot be cited.
"""

from __future__ import annotations

#: The API the files came from. ``{annex}`` is II, III, IV, V or VI.
SOURCE_URL = (
    "https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/{annex}/export-csv"
)

#: Publisher, for attribution. The data is European Commission material, reusable
#: under Commission Decision 2011/833/EU; the Commission's own legal notice states
#: that content it owns is licensed CC BY 4.0.
SOURCE_ATTRIBUTION = (
    "CosIng, © European Union, 1995-2026. Annexes II to VI of Regulation (EC) "
    "No 1223/2009, retrieved from the European Commission CosIng API. Reused "
    "under Commission Decision 2011/833/EU (CC BY 4.0). Unmodified."
)

#: The date these files were downloaded, in ISO form.
RETRIEVED = "2026-09-09"

#: One record per annex. ``last_update`` and ``file_creation_date`` are the
#: Commission's own, read out of rows 1 and 0 of each CSV, in DD/MM/YYYY.
ANNEXES: dict[str, dict[str, object]] = {
    "II": {
        "filename": "annex_II.csv",
        "title": "LIST OF SUBSTANCES PROHIBITED IN COSMETIC PRODUCTS",
        "sha256": "b7105a05bf724bb10cebaac3a3813b6146c3153ae1d07097d35bb1f73cd7283b",
        "size": 650518,
        "file_creation_date": "09/09/2026",
        "last_update": "28/08/2026",
        "data_rows": 1758,
    },
    "III": {
        "filename": "annex_III.csv",
        "title": (
            "LIST OF SUBSTANCES WHICH COSMETIC PRODUCTS MUST NOT CONTAIN "
            "EXCEPT SUBJECT TO THE RESTRICTIONS LAID DOWN"
        ),
        "sha256": "82263556bab69a05b508b92e42dbeceec56f201a62ded2dd513198f6b029dd53",
        "size": 296566,
        "file_creation_date": "09/09/2026",
        "last_update": "28/08/2026",
        "data_rows": 381,
    },
    "IV": {
        "filename": "annex_IV.csv",
        "title": "LIST OF COLORANTS ALLOWED IN COSMETIC PRODUCTS",
        "sha256": "bed185d597cec2e119b05eb8fb43adc07d3ddc1aa6ed0a2ee64308f790b5b84b",
        "size": 47319,
        "file_creation_date": "09/09/2026",
        "last_update": "28/08/2026",
        "data_rows": 154,
    },
    "V": {
        "filename": "annex_V.csv",
        "title": "LIST OF PRESERVATIVES ALLOWED IN COSMETIC PRODUCTS",
        "sha256": "e6db8b8b90d4082ec83bcc9d1fffcd8993b501d1e8116de057c772a347d10b12",
        "size": 31439,
        "file_creation_date": "09/09/2026",
        "last_update": "28/08/2026",
        "data_rows": 58,
    },
    "VI": {
        "filename": "annex_VI.csv",
        "title": "LIST OF UV FILTERS ALLOWED IN COSMETIC PRODUCTS",
        "sha256": "b672b81a2a090b56bf09bbd554764a6f0c8dd8104761a0e87933e555df775774",
        "size": 19161,
        "file_creation_date": "09/09/2026",
        "last_update": "28/08/2026",
        "data_rows": 34,
    },
}

#: The order the annexes are reported in. Numerical, as the Regulation has them.
ORDER = ("II", "III", "IV", "V", "VI")

#: Files inside the package that are not Python source. Anything else found in
#: the package directory is a stray, and the offline test fails on it.
DECLARED_DATA_FILES = frozenset(
    str(record["filename"]) for record in ANNEXES.values()
)
