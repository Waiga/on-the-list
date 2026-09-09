"""The four checks, against the register as shipped.

The class names are the claims. If one of them stops being true, the test that
fails says which claim broke.
"""

from __future__ import annotations

import unittest

from on_the_list.analyse import analyse
from on_the_list.register import load

REGISTER = load()


def run(text: str, **kwargs):
    return analyse(ingredients_text=text, register=REGISTER, **kwargs)


def checks_of(report, name):
    return [f for f in report.findings if f.check == name]


class AProhibitedNameIsReportedAsAMatchAndNotAsAVerdict(unittest.TestCase):
    def test_an_unconditional_entry_is_found(self):
        report = run("Aqua, Glycerin, Butylphenyl Methylpropional, Parfum")
        found = checks_of(report, "prohibited")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].citation, "Annex II, entry 1666")
        self.assertFalse(found[0].qualified)

    def test_it_never_says_illegal_unsafe_or_non_compliant(self):
        report = run("Aqua, Formaldehyde, Butylphenyl Methylpropional")
        words = " ".join(
            [f.summary + " " + " ".join(f.detail) for f in report.findings]
        ).lower()
        for forbidden in (
            "illegal", "unlawful", "non-compliant", "noncompliant", "unsafe",
            "banned", "violation", "breach",
        ):
            self.assertNotIn(forbidden, words)

    def test_a_conditional_entry_is_reported_separately_with_its_condition(self):
        report = run("Aqua, Petrolatum, Glycerin")
        found = checks_of(report, "prohibited")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].qualified)
        self.assertIn("except if", found[0].summary)
        self.assertIn(
            "refining history", " ".join(found[0].detail)
        )

    def test_a_nano_only_entry_is_considered_and_not_counted(self):
        report = run("Aqua, Styrene/Acrylates Copolymer, Glycerin")
        self.assertEqual(checks_of(report, "prohibited"), [])
        self.assertEqual(len(report.considered), 1)
        self.assertIn("nanomaterial", report.considered[0].reason)

    def test_but_the_same_name_marked_nano_is_reported(self):
        report = run("Aqua, Styrene/Acrylates Copolymer (nano), Glycerin")
        self.assertEqual(len(checks_of(report, "prohibited")), 1)

    def test_a_match_on_a_fragment_of_the_name_is_not_reported(self):
        # "CI 77288 / CHROMIUM" is a colourant printed with its element name.
        # Matching the fragment against the Annex II entry for chromium metal
        # is not good enough to report, so it is shown as considered instead.
        report = run("Aqua, CI 77288 / CHROMIUM, Glycerin")
        self.assertEqual(checks_of(report, "prohibited"), [])
        self.assertTrue(report.considered)
        self.assertIn("part of what is printed", report.considered[0].reason)

    def test_a_bracketed_aside_does_not_stop_a_whole_name_matching(self):
        report = run("Aqua, Butylphenyl Methylpropional (fragrance allergen)")
        self.assertEqual(len(checks_of(report, "prohibited")), 1)

    def test_a_prohibition_qualified_by_another_annex_says_so(self):
        # Annex II entry 1329 prohibits Hydroquinone "with the exception of
        # entry 14 in Annex III", where it is allowed in professional nail
        # products. Reporting only the prohibition would be a half-truth.
        report = run("Aqua, Hydroquinone")
        found = checks_of(report, "prohibited")
        self.assertEqual(len(found), 1)
        self.assertIn("Annex III, entry 14", " ".join(found[0].detail))


class ColourantPositionIsReportedWithoutJudgement(unittest.TestCase):
    def test_a_colour_index_before_a_non_colourant(self):
        report = run("Aqua, CI 77491, Glycerin, Parfum")
        found = checks_of(report, "colourant-order")
        self.assertEqual(len(found), 1)
        self.assertIn("Glycerin", " ".join(found[0].detail))

    def test_a_colour_index_at_the_end_is_not_a_finding(self):
        report = run("Aqua, Glycerin, Parfum, CI 77491, CI 77492")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_the_shade_range_block_is_not_looked_at(self):
        report = run("Aqua, Glycerin [+/- CI 77491, CI 77492]")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_a_named_dual_use_substance_is_deliberately_not_used(self):
        # Titanium Dioxide is an Annex IV colourant, an Annex VI UV filter and
        # an opacifier. Its position proves nothing about which it is doing.
        report = run("Aqua, Titanium Dioxide, Glycerin, Parfum")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_a_colourant_printed_under_two_names_is_still_a_colourant(self):
        # "CI 77891 / TITANIUM DIOXIDE" following "CI 77491" is not a
        # non-colourant, and counting it as one inflated the finding.
        report = run("Aqua, Glycerin, CI 77491, CI 77891 / TITANIUM DIOXIDE")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_a_lake_suffix_is_still_a_colourant(self):
        report = run("Aqua, Glycerin, CI 77491, CI 15850:1")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_an_ocr_lowercase_l_is_read_as_a_colour_index(self):
        report = run("Aqua, Glycerin, CI 77491, Cl 77492")
        self.assertEqual(checks_of(report, "colourant-order"), [])

    def test_the_position_is_written_as_an_ordinal(self):
        report = run("Aqua, Glycerin, CI 77491, Parfum")
        self.assertIn("printed 3rd", checks_of(report, "colourant-order")[0].summary)

    def test_the_caveats_are_printed_with_every_finding(self):
        report = run("Aqua, CI 77491, Glycerin")
        detail = " ".join(checks_of(report, "colourant-order")[0].detail)
        self.assertIn("hair colourants", detail)
        self.assertIn("below 1%", detail)


class RepeatedEntriesNeedNoRegister(unittest.TestCase):
    def test_one_name_printed_twice(self):
        report = run("Aqua, Glycerin, Parfum, Glycerin")
        found = checks_of(report, "repeated-entry")
        self.assertEqual(len(found), 1)
        self.assertIn("positions 2, 4", found[0].summary)

    def test_a_list_printed_twice_is_one_finding_about_the_list(self):
        one = "Aqua, Glycerin, Parfum, Tocopherol, Citric Acid, Sodium Chloride"
        report = run(one + ", " + one)
        found = checks_of(report, "repeated-entry")
        self.assertEqual(len(found), 1)
        self.assertIn("printed more than once", found[0].summary)

    def test_a_name_in_both_the_list_and_the_shade_block_is_not_a_repeat(self):
        report = run("Aqua, CI 77491 [+/- CI 77491, CI 77492]")
        self.assertEqual(checks_of(report, "repeated-entry"), [])

    def test_it_does_not_run_when_the_field_holds_more_than_one_list(self):
        report = run("MASQUE: Aqua, Glycerin. GEL: Aqua, Parfum")
        state = {c.name: c for c in report.checks}
        self.assertFalse(state["repeated-entry"].ran)
        self.assertFalse(state["colourant-order"].ran)
        self.assertIn("more than one section", state["repeated-entry"].reason)
        # The register-based checks are unaffected: they do not care about
        # order.
        self.assertTrue(state["prohibited"].ran)


class MissingWarningWordingIsAGapNotAViolation(unittest.TestCase):
    LIST = "Aqua, Sorbitol, Sodium Fluoride, Aroma"

    def test_it_does_not_run_without_pack_text(self):
        report = run(self.LIST)
        state = {c.name: c for c in report.checks}
        self.assertFalse(state["warning-wording"].ran)
        self.assertIn("no pack text", state["warning-wording"].reason)

    def test_a_missing_statement_is_reported(self):
        report = run(self.LIST, pack_text="Fresh mint toothpaste. 75 ml.")
        found = checks_of(report, "warning-wording")
        self.assertEqual(len(found), 1)
        self.assertIn("Contains sodium fluoride", found[0].summary)

    def test_a_present_statement_is_not(self):
        report = run(
            self.LIST,
            pack_text="Fresh mint toothpaste. Contains sodium fluoride.",
        )
        self.assertEqual(checks_of(report, "warning-wording"), [])

    def test_the_wording_is_matched_after_folding_both_sides(self):
        report = run(self.LIST, pack_text="CONTAINS  SODIUM   FLUORIDE")
        self.assertEqual(checks_of(report, "warning-wording"), [])

    def test_the_finding_says_it_is_a_gap_and_shows_the_full_wording(self):
        report = run(self.LIST, pack_text="Toothpaste")
        detail = " ".join(checks_of(report, "warning-wording")[0].detail)
        self.assertIn("gap in what was supplied", detail)
        self.assertIn("wording in full", detail)


class WordingThatIsNotSearchedForIsStillReported(unittest.TestCase):
    """A wording the tool will not look for must not vanish silently.

    It is named compactly. An earlier version printed each entry's full
    chemical name, which put twenty lines of naphthalenesulphonate above the
    findings for one lipstick.
    """

    LIST = "Aqua, CI 16035, CI 14720, CI 15850, CI 19140, Glycerin"

    def test_it_is_counted_and_each_entry_is_named(self):
        limits = " ".join(run(self.LIST, pack_text="Lipstick").limits)
        self.assertIn("4 annex entries", limits)
        self.assertIn("CI 16035 (Annex IV, entry 32)", limits)

    def test_it_is_one_line_not_one_per_entry(self):
        report = run(self.LIST, pack_text="Lipstick")
        about = [x for x in report.limits if "does not search for" in x]
        self.assertEqual(len(about), 1)


class CoverageIsReportedAsAbsenceOfRestrictionNotAsIgnorance(unittest.TestCase):
    def test_unrestricted_ingredients_are_counted_not_flagged(self):
        report = run("Aqua, Glycerin, Parfum")
        self.assertEqual(len(report.unrestricted), 3)
        self.assertEqual(report.findings, [])

    def test_no_check_treats_absence_from_the_annexes_as_a_defect(self):
        report = run("Notarealingredient, Anotherinventedname, Aqua")
        self.assertEqual(report.findings, [])
        self.assertEqual(len(report.unrestricted), 3)


class ChecksCanBeSwitchedOffAndTheReportSaysSo(unittest.TestCase):
    def test_skipping_one_check(self):
        report = run(
            "Aqua, Butylphenyl Methylpropional, CI 77491, Glycerin",
            skip=frozenset({"prohibited"}),
        )
        state = {c.name: c for c in report.checks}
        self.assertFalse(state["prohibited"].ran)
        self.assertIn("--skip", state["prohibited"].reason)
        self.assertEqual(checks_of(report, "prohibited"), [])
        self.assertTrue(checks_of(report, "colourant-order"))

    def test_every_check_appears_in_the_report_whether_it_ran_or_not(self):
        report = run("Aqua, Glycerin")
        self.assertEqual(len(report.checks), 4)
        for run_record in report.checks:
            if not run_record.ran:
                self.assertTrue(run_record.reason)


class WhenThereIsNoListNothingIsClaimed(unittest.TestCase):
    def test_a_label_without_a_heading(self):
        report = analyse(
            label_text="A rich cream for dry skin.", register=REGISTER
        )
        self.assertFalse(report.parsed)
        self.assertEqual(report.findings, [])
        self.assertTrue(all(not c.ran for c in report.checks))
        self.assertTrue(report.limits)

    def test_a_binary_file(self):
        report = analyse(
            ingredients_text="PK\x03\x04" + "\x00" * 200, register=REGISTER
        )
        self.assertFalse(report.parsed)
        self.assertIn("not printable text", " ".join(report.limits))


class ThePanelIsReportedAsDirtyWhenItIs(unittest.TestCase):
    def test_prose_inside_the_panel_is_flagged(self):
        report = run(
            "Aqua, Glycerin, this rinse is not intended to replace brushing "
            "or flossing, Parfum"
        )
        self.assertIn("pack prose", " ".join(report.limits))

    def test_a_clean_list_is_not(self):
        report = run("Aqua, Glycerin, Parfum")
        self.assertNotIn("pack prose", " ".join(report.limits))


if __name__ == "__main__":
    unittest.main()
