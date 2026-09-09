"""Reading the Commission's CSVs.

Almost every case here is a real row that a simpler rule got wrong. The
separator cases in particular are not hypothetical: a plain ``split(",")`` puts
a substance called ``N`` into the register, and then a label containing the
letter N in a token by itself matches a prohibited substance.
"""

from __future__ import annotations

import unittest

from on_the_list.annexes import (
    is_nano_only,
    label_phrases,
    qualifier_in,
    read_annex,
    read_header_dates,
    split_glossary,
    split_identified,
)


class TheGlossaryColumnSplitsOnSemicolonAndSlashOnly(unittest.TestCase):
    def test_slash_separated_salts(self):
        self.assertEqual(
            split_glossary("AMMONIUM BENZOATE / BUTYL BENZOATE / CALCIUM BENZOATE"),
            ["AMMONIUM BENZOATE", "BUTYL BENZOATE", "CALCIUM BENZOATE"],
        )

    def test_semicolon_separated_names(self):
        self.assertEqual(
            split_glossary("p-Phenylenediamine; p-Phenylenediamine HCl"),
            ["p-Phenylenediamine", "p-Phenylenediamine HCl"],
        )

    def test_a_comma_inside_a_name_is_not_a_separator(self):
        # Annex III entry 1. Splitting on the comma yields "1-HEXYL 4", which
        # is not a substance and matches nothing for ever after.
        self.assertEqual(
            split_glossary("1-HEXYL 4,5-DIAMINO PYRAZOLE SULFATE"),
            ["1-HEXYL 4,5-DIAMINO PYRAZOLE SULFATE"],
        )

    def test_the_dash_placeholder_is_not_a_name(self):
        self.assertEqual(split_glossary("-"), [])
        self.assertEqual(split_glossary(""), [])


class TheIdentifiedColumnKeepsCommasThatBelongToNames(unittest.TestCase):
    """Every one of these is a row in the September 2026 files."""

    CASES = [
        (
            "1,3-Bis(hydroxymethyl)-3-thiourea,Hydroxymethyl-2-thiourea,"
            "1-Hydroxymethylimidazolidine-2-thione,"
            "1-Monomorpholinomethyl-2-thiourea,"
            "1,3-Bis(morpholinomethyl)-2-thiourea,THIOUREA",
            [
                "1,3-Bis(hydroxymethyl)-3-thiourea",
                "Hydroxymethyl-2-thiourea",
                "1-Hydroxymethylimidazolidine-2-thione",
                "1-Monomorpholinomethyl-2-thiourea",
                "1,3-Bis(morpholinomethyl)-2-thiourea",
                "THIOUREA",
            ],
        ),
        (
            "N,N-DIETHYL-m-AMINOPHENOL,N,N-DIETHYL-m-AMINOPHENOL SULFATE",
            ["N,N-DIETHYL-m-AMINOPHENOL", "N,N-DIETHYL-m-AMINOPHENOL SULFATE"],
        ),
        # The one that needs both halves of the rule: the fragment before the
        # comma ends in a digit and the fragment after starts with one.
        ("PEG-3,2',2'-Di-p-PHENYLENEDIAMINE", ["PEG-3,2',2'-Di-p-PHENYLENEDIAMINE"]),
        # The mirror case: a digit follows the comma but the fragment before it
        # is an ordinary word, so the comma really is a separator.
        (
            "DICHLOROMETHANE,4,6-DIMETHYL-PYRAN-2-ONE",
            ["DICHLOROMETHANE", "4,6-DIMETHYL-PYRAN-2-ONE"],
        ),
        # And its opposite: a digit before the comma, an ordinary word after.
        ("CI 77480,GOLD", ["CI 77480", "GOLD"]),
        ("1,2,4-BENZENETRIACETATE", ["1,2,4-BENZENETRIACETATE"]),
        (
            "4,6-BIS(2-HYDROXYETHOXY)-m-PHENYLENEDIAMINE HCl,"
            "4,6-BIS(2-HYDROXYETHOXY)-m-PHENYLENEDIAMINE",
            [
                "4,6-BIS(2-HYDROXYETHOXY)-m-PHENYLENEDIAMINE HCl",
                "4,6-BIS(2-HYDROXYETHOXY)-m-PHENYLENEDIAMINE",
            ],
        ),
        (",PABA,GLYCERYL PABA,BUTYL PABA", ["PABA", "GLYCERYL PABA", "BUTYL PABA"]),
        ("", []),
    ]

    def test_every_case(self):
        for value, expected in self.CASES:
            with self.subTest(value=value[:40]):
                self.assertEqual(split_identified(value), expected)


class TheWordingYieldsOnlyContainsStatements(unittest.TestCase):
    def test_a_contains_statement_on_its_own_line(self):
        self.assertEqual(
            label_phrases("Conditions of use:\nContains thioglycolate\nFollow"),
            ("Contains thioglycolate",),
        )

    def test_a_contains_statement_after_a_qualifier_on_the_same_line(self):
        self.assertEqual(
            label_phrases("Above 2%: Contains ammonia"), ("Contains ammonia",)
        )

    def test_a_footnote_marker_is_dropped(self):
        self.assertEqual(
            label_phrases("For a) and b): Contains Benzophenone-3 (*) "),
            ("Contains Benzophenone-3",),
        )

    def test_a_purity_condition_yields_nothing(self):
        # Annex IV. Not label text at all, and treating it as label text would
        # report a missing warning on every product containing the colourant.
        self.assertEqual(
            label_phrases(
                "Purity criteria as set out in Commission Directive 95/45/EC "
                "(E 129)"
            ),
            (),
        )

    def test_a_manufacturing_condition_yields_nothing(self):
        self.assertEqual(
            label_phrases(
                "Not to be used in applications that may lead to exposure of "
                "the end-user's lungs by inhalation."
            ),
            (),
        )

    def test_a_statement_does_not_run_into_the_next_sentence(self):
        self.assertEqual(
            label_phrases(
                "Contains phenylenediamines. Do not use to dye eyelashes."
            ),
            ("Contains phenylenediamines",),
        )

    def test_a_newline_ends_a_statement(self):
        # This is why the reader uses io.StringIO. Feeding csv.reader a list of
        # lines glues the two together into one run-on phrase.
        self.assertEqual(
            label_phrases("Contains selenium disulphide\nAvoid contact with eyes"),
            ("Contains selenium disulphide",),
        )


class QualifiersAndNanoForms(unittest.TestCase):
    def test_the_conditional_words_are_found(self):
        for text, expected in (
            (
                "Petrolatum, except if the full refining history is known",
                "except if",
            ),
            ("(Pigment Blue 15; CI 74160) when used as a substance", "when used"),
            ("Furocoumarines ... except for normal content", "except for"),
            ("Isobutane, if it contains = >0,1% w/w Butadiene", "if"),
        ):
            with self.subTest(text=text[:40]):
                self.assertEqual(qualifier_in(text), expected)

    def test_an_unconditional_entry_has_no_qualifier(self):
        self.assertEqual(qualifier_in("2-(4-tert-butylbenzyl) propionaldehyde"), "")
        self.assertEqual(qualifier_in("Formaldehyde"), "")

    def test_a_nano_entry_whose_names_do_not_say_nano(self):
        self.assertTrue(
            is_nano_only(
                "Styrene/Acrylates copolymer (nano) [INCI]",
                ("STYRENE/ACRYLATES COPOLYMER",),
            )
        )

    def test_a_nano_entry_whose_names_do_say_nano(self):
        self.assertFalse(
            is_nano_only("Titanium dioxide (nano)", ("TITANIUM DIOXIDE (NANO)",))
        )

    def test_an_ordinary_entry(self):
        self.assertFalse(is_nano_only("Formaldehyde", ("FORMALDEHYDE",)))


MINI = (
    '"File creation date: 09/09/2026"\n'
    '"ANNEX V","Last update: 28/08/2026"\n'
    '"LIST OF PRESERVATIVES ALLOWED IN COSMETIC PRODUCTS"\n'
    '"Substance identification",Conditions\n'
    '"Reference Number","Chemical name / INN",'
    '"Name of Common Ingredients Glossary","Product Type, body parts",'
    '"Wording of conditions of use and warnings",'
    '"Identified INGREDIENTS or substances e.g.","Update Date"\n'
    '"12","Testolate and its salts","ALPHA TESTOLATE / BETA TESTOLATE",'
    '"Rinse-off only","Conditions of use:\nContains testolate\nKeep away",'
    '"ALPHA TESTOLATE,N,N-TESTOLAMINE","01/01/2026"\n'
)


class ReadingAWholeFile(unittest.TestCase):
    def test_header_dates(self):
        self.assertEqual(read_header_dates(MINI), ("09/09/2026", "28/08/2026"))

    def test_one_row_becomes_one_entry_with_every_name(self):
        entries = read_annex("V", MINI)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.citation, "Annex V, entry 12")
        self.assertEqual(entry.chemical_name, "Testolate and its salts")
        self.assertEqual(entry.product_types, "Rinse-off only")
        self.assertIn("ALPHA TESTOLATE", entry.names)
        self.assertIn("BETA TESTOLATE", entry.names)
        self.assertIn("N,N-TESTOLAMINE", entry.names)
        self.assertEqual(entry.label_phrases, ("Contains testolate",))

    def test_a_name_appearing_in_both_columns_is_kept_once(self):
        entry = read_annex("V", MINI)[0]
        folded = [name for name, _ in entry.normalised_names]
        self.assertEqual(len(folded), len(set(folded)))
        self.assertEqual(folded.count("alpha testolate"), 1)

    def test_the_glossary_column_wins_for_a_name_in_both(self):
        entry = read_annex("V", MINI)[0]
        source = dict(entry.normalised_names)["alpha testolate"]
        self.assertEqual(source, "glossary")

    def test_a_file_without_the_expected_header_is_refused(self):
        broken = "a\nb\nc\nd\nnot,the,header\n1,2,3\n"
        with self.assertRaises(ValueError):
            read_annex("V", broken)

    def test_a_file_too_short_to_hold_a_header_is_refused(self):
        with self.assertRaises(ValueError):
            read_annex("V", "one\ntwo\n")


if __name__ == "__main__":
    unittest.main()
