"""The five annexes, loaded and indexed by name.

Loading is offline in every path. The bytes come either from the copy shipped
inside the package or from a directory on disk that ``on-the-list
update-register`` wrote earlier. Nothing in this module knows how to fetch
anything, which is checked by a test rather than promised in a docstring.

The index is a plain dictionary from a folded name to the entries carrying it.
There is no fuzzy matching, no substring search, no nearest neighbour. Given a
prohibited-substances list, a near-match is worse than no match: it produces a
confident finding about a substance the label does not contain.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from on_the_list import registry_manifest as manifest
from on_the_list.annexes import read_annex, read_header_dates
from on_the_list.models import AnnexEntry, RegisterInfo
from on_the_list.normalise import is_colour_index

#: The directory the vendored copy lives in.
VENDORED = Path(__file__).resolve().parent / "data"


class RegisterError(Exception):
    """The register could not be loaded, and the run must stop."""


@dataclass(frozen=True)
class Register:
    entries: tuple[AnnexEntry, ...]
    #: folded name -> entries naming it, in annex order.
    by_name: dict[str, tuple[AnnexEntry, ...]]
    info: RegisterInfo

    def lookup(self, folded: str) -> tuple[AnnexEntry, ...]:
        return self.by_name.get(folded, ())

    @property
    def colour_index_names(self) -> frozenset[str]:
        return frozenset(n for n in self.by_name if is_colour_index(n))


def _load_files(directory: Path, origin: str, verify: bool) -> Register:
    entries: list[AnnexEntry] = []
    info_annexes: dict[str, tuple[str, str, int]] = {}
    for annex in manifest.ORDER:
        record = manifest.ANNEXES[annex]
        path = directory / str(record["filename"])
        if not path.is_file():
            raise RegisterError(
                f"{path} is missing. Run 'on-the-list update-register' to "
                "download the annexes, or point --register at a directory "
                "holding them."
            )
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if verify and digest != record["sha256"]:
            raise RegisterError(
                f"{path} is not the file this package was built against.\n"
                f"  expected sha256 {record['sha256']}\n"
                f"  found    sha256 {digest}\n"
                "The vendored copy must not be edited. Delete it and "
                "reinstall, or use --register to read a different directory."
            )
        text = raw.decode("utf-8")
        _, last_update = read_header_dates(text)
        rows = read_annex(annex, text)
        entries.extend(rows)
        info_annexes[annex] = (last_update, digest, len(rows))

    by_name: dict[str, list[AnnexEntry]] = {}
    for entry in entries:
        for name, _ in entry.normalised_names:
            by_name.setdefault(name, []).append(entry)

    return Register(
        entries=tuple(entries),
        by_name={name: tuple(rows) for name, rows in by_name.items()},
        info=RegisterInfo(
            origin=origin,
            annexes=info_annexes,
            name_count=len(by_name),
        ),
    )


def load(source: str | Path | None = None) -> Register:
    """Load the register.

    ``source`` may be a directory holding the five annex CSVs. With no
    argument, a register downloaded by ``update-register`` is preferred over
    the vendored copy, because a user who bothered to download one wants the
    newer file; if there is none, the vendored copy is used.

    The vendored copy is hash-checked against ``registry_manifest``. A
    downloaded or user-supplied one is not: it is expected to differ, and the
    report names its hash instead so the reader can see which version produced
    the result.
    """
    if source is not None:
        directory = Path(source)
        return _load_files(directory, f"{directory}", verify=False)

    from on_the_list.paths import register_dir

    cached = register_dir()
    if all(
        (cached / str(record["filename"])).is_file()
        for record in manifest.ANNEXES.values()
    ):
        return _load_files(cached, f"{cached} (downloaded)", verify=False)
    return _load_files(
        VENDORED, "the copy shipped with this package", verify=True
    )


def describe(register: Register) -> list[str]:
    """A few lines naming exactly which register a report was produced against.

    Printed in full by ``on-the-list register``. The point is that a result is
    citable: anyone can re-download the same annex and compare the hash.
    """
    lines = [register.info.line(), ""]
    lines.append(manifest.SOURCE_ATTRIBUTION)
    lines.append("")
    for annex in manifest.ORDER:
        last_update, digest, rows = register.info.annexes[annex]
        title = str(manifest.ANNEXES[annex]["title"])
        lines.append(f"Annex {annex} — {title.lower()}")
        lines.append(f"  {rows} entries, Commission last update {last_update}")
        lines.append(f"  sha256 {digest}")
        lines.append(
            "  " + manifest.SOURCE_URL.format(annex=annex)
        )
    return lines

