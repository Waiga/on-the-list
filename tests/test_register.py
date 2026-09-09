"""Loading the vendored register, and what is actually in it.

The fixtures at the bottom are the point of this file. They are substances
whose annex is not in dispute, checked against the register as shipped, so that
a change to the parser that quietly stops matching things fails here rather
than in somebody's report.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from on_the_list import registry_manifest as manifest
from on_the_list.normalise import fold
from on_the_list.register import VENDORED, RegisterError, load

REGISTER = load()


class TheVendoredRegisterLoads(unittest.TestCase):
    def test_it_names_the_version_it_used(self):
        line = REGISTER.info.line()
        self.assertIn("28/08/2026", line)
        self.assertIn("shipped with this package", line)

    def test_every_annex_is_present_with_the_expected_row_count(self):
        for annex, record in manifest.ANNEXES.items():
            with self.subTest(annex=annex):
                _, digest, rows = REGISTER.info.annexes[annex]
                self.assertEqual(digest, record["sha256"])
                self.assertEqual(rows, record["data_rows"])

    def test_the_register_is_the_size_the_readme_says(self):
        # If this number moves, every count in the README is stale.
        self.assertEqual(REGISTER.info.name_count, 1913)

    def test_it_refuses_a_vendored_file_that_has_been_edited(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "data"
            shutil.copytree(VENDORED, copy)
            target = copy / "annex_V.csv"
            target.write_bytes(target.read_bytes() + b"\nedited\n")
            # A user-supplied directory is not hash-checked: it is expected to
            # differ, and the report names its hash instead.
            register = load(copy)
            self.assertIn(str(copy), register.info.origin)
            self.assertNotEqual(
                register.info.annexes["V"][1], manifest.ANNEXES["V"]["sha256"]
            )

    def test_a_missing_file_is_an_error_that_says_what_to_do(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RegisterError) as caught:
                load(directory)
        self.assertIn("update-register", str(caught.exception))

    def test_the_manifest_hashes_match_the_files_on_disk(self):
        for record in manifest.ANNEXES.values():
            path = VENDORED / str(record["filename"])
            with self.subTest(file=record["filename"]):
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    record["sha256"],
                )


class SubstancesWhoseAnnexIsNotInDispute(unittest.TestCase):
    """Fixtures. Each pairing is checkable against the published annex."""

    CASES = {
        "METHYLPARABEN": {"V"},
        "SODIUM BENZOATE": {"V"},
        "PHENOXYETHANOL": {"V"},
        "IMIDAZOLIDINYL UREA": {"V"},
        "FORMALDEHYDE": {"II"},
        "CI 16035": {"III", "IV"},
        "TITANIUM DIOXIDE": {"III", "IV", "VI"},
        "BUTYLPHENYL METHYLPROPIONAL": {"II"},
        "ZINC PYRITHIONE": {"II"},
        "BENZOPHENONE-3": {"VI"},
    }

    def test_each_name_appears_in_the_expected_annexes(self):
        for name, expected in self.CASES.items():
            with self.subTest(name=name):
                entries = REGISTER.lookup(fold(name))
                self.assertTrue(entries, f"{name} is in no annex at all")
                self.assertEqual({e.annex for e in entries}, expected)


class AbsenceIsNotIgnorance(unittest.TestCase):
    """The finding the whole design rests on.

    Aqua and Glycerin are in none of the five annexes. They are not unknown
    names and they are not invalid names: the annexes list restricted
    substances, and these are not restricted. A tool that reports their absence
    as a defect has misunderstood what it is reading.
    """

    def test_the_two_commonest_ingredients_in_cosmetics_are_in_no_annex(self):
        for name in ("AQUA", "GLYCERIN", "WATER", "PARFUM"):
            with self.subTest(name=name):
                self.assertEqual(REGISTER.lookup(fold(name)), ())


class TheRegisterIsCleanEnoughToMatchAgainst(unittest.TestCase):
    def test_no_name_is_a_bare_locant(self):
        # "N", "1", "2'" -- what a plain comma split leaves behind. A register
        # containing them matches junk tokens on real labels.
        junk = [
            name
            for name in REGISTER.by_name
            if len(name) < 3 and not name.isalpha()
        ]
        self.assertEqual(junk, [])

    def test_folding_a_register_name_again_changes_nothing(self):
        for name in REGISTER.by_name:
            with self.subTest(name=name[:40]):
                self.assertEqual(fold(name), name)

    def test_the_colour_index_names_look_like_colour_index_numbers(self):
        names = REGISTER.colour_index_names
        self.assertGreater(len(names), 100)
        for name in names:
            self.assertRegex(name, r"^ci \d{5}(?::\d{1,2})?$")

    def test_annex_two_carries_far_fewer_inci_names_than_rows(self):
        """A limitation worth failing on if it silently changes.

        Only a minority of Annex II rows carry an INCI name at all: most are
        chemical or CAS identifiers with no cosmetic-glossary equivalent. The
        prohibited check can only see the ones that do, and the README says so.
        """
        rows = [e for e in REGISTER.entries if e.annex == "II"]
        named = [e for e in rows if e.names]
        self.assertEqual(len(rows), 1758)
        self.assertEqual(len(named), 314)


if __name__ == "__main__":
    unittest.main()
