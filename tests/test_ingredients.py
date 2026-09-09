"""Parsing a printed ingredient list.

Most of these are real pack text. The HTML-entity case and the fluoride
declaration in particular are defects that only appeared when the tool met
16,635 published labels, and each one produced a wrong finding rather than an
error.
"""

from __future__ import annotations

import unittest

from on_the_list.ingredients import (
    component_headings,
    extract,
    looks_binary,
    looks_like_prose,
    parse,
    trim,
)


class FindingTheListInsideALabel(unittest.TestCase):
    def test_a_heading_in_english(self):
        block, found = extract("BRIGHT CREAM\n\nIngredients: Aqua, Glycerin.")
        self.assertTrue(found)
        self.assertIn("Aqua", block)
        self.assertNotIn("BRIGHT", block)

    def test_a_heading_in_another_language(self):
        for heading in ("Ingrédients", "Inhaltsstoffe", "Ingredientes", "INCI"):
            with self.subTest(heading=heading):
                _, found = extract(f"{heading}: Aqua, Glycerin.")
                self.assertTrue(found)

    def test_no_heading_means_nothing_is_read(self):
        # Guessing would be worse. A paragraph of marketing copy treated as an
        # ingredient list produces confident nonsense.
        block, found = extract("A rich cream for dry skin. Dermatologist tested.")
        self.assertFalse(found)
        self.assertEqual(block, "")

    def test_the_list_stops_at_the_next_panel(self):
        block, _ = extract("Ingredients: Aqua, Glycerin.\nDirections: apply.")
        self.assertNotIn("apply", block)

    def test_the_next_panel_is_recognised_in_the_other_pack_languages(self):
        # A European pack prints its panels in every language it sells in, and
        # an English-only terminator read "Précautions: éviter le contact avec
        # les yeux" as an ingredient.
        for panel in (
            "Précautions: éviter le contact avec les yeux.",
            "Mode d'emploi: appliquer le matin.",
            "Anwendung: morgens auftragen.",
            "Modo de uso: aplicar.",
            "Avvertenze: evitare il contatto con gli occhi.",
            "Gebruiksaanwijzing: aanbrengen.",
            "Advarsel: unngå kontakt med øynene.",
        ):
            with self.subTest(panel=panel):
                block, _ = extract(f"Ingredients: Aqua, Glycerin.\n{panel}")
                self.assertNotIn(panel.split(":")[1].strip(), block)

    def test_the_same_panel_run_on_from_the_list_inline(self):
        block, _ = extract("Ingredients: Aqua, Glycerin. Modo de uso: aplicar.")
        self.assertNotIn("aplicar", block)

    def test_a_panel_word_inside_a_real_name_does_not_cut_the_list(self):
        # The inline rule needs the colon, because "application", "usage",
        # "purpose" and "attention" are ordinary enough to appear in a name.
        block, _ = extract("Ingredients: Aqua, Application Extract, Glycerin.")
        self.assertIn("Glycerin", block)


class TrimmingAPanelThatIsNotAList(unittest.TestCase):
    def test_a_fluoride_content_declaration_is_cut_off(self):
        # The commonest reason a colourant appeared to be printed in front of a
        # non-colourant: the declaration runs on from the list with no break.
        block, dropped = trim(
            "Aqua, Sorbitol, CI 74160, CI 77891. "
            "Contient du fluorure de sodium (1450 ppm de fluor)"
        )
        self.assertNotIn("fluorure", block)
        self.assertIn("fluorure", dropped)

    def test_the_same_in_the_other_languages_it_appears_in(self):
        for text in (
            "Aqua, CI 77891. inneholder: natriumfluorid (1450ppm F)",
            "Aqua, CI 77891. Contains: Sodium Fluoride 0,32% w/w",
            "Aqua, CI 77891. Enthält Natriumfluorid (1450 ppm Fluorid)",
        ):
            with self.subTest(text=text[-40:]):
                block, dropped = trim(text)
                self.assertTrue(dropped.strip())
                self.assertIn("CI 77891", block)

    def test_an_ingredient_list_using_the_word_contains_is_untouched(self):
        # The declaration is recognised by the concentration it carries, not by
        # the word alone.
        text = "Aqua, Glycerin, Contains Nothing Extract, Parfum"
        block, dropped = trim(text)
        self.assertEqual(dropped, "")
        self.assertEqual(block, text)

    def test_nothing_to_trim(self):
        self.assertEqual(trim("Aqua, Glycerin"), ("Aqua, Glycerin", ""))


class SplittingIntoIngredients(unittest.TestCase):
    def test_order_and_index_are_preserved(self):
        items = parse("Aqua, Glycerin, Parfum")
        self.assertEqual([i.raw for i in items], ["Aqua", "Glycerin", "Parfum"])
        self.assertEqual([i.index for i in items], [1, 2, 3])

    def test_a_comma_inside_brackets_does_not_split(self):
        items = parse("Butyrospermum Parkii (Shea, Karite) Butter, Aqua")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].raw, "Butyrospermum Parkii (Shea, Karite) Butter")

    def test_a_supplier_blend_is_two_ingredients(self):
        items = parse("Phenoxyethanol (and) Ethylhexylglycerin")
        self.assertEqual([i.raw for i in items], ["Phenoxyethanol", "Ethylhexylglycerin"])

    def test_percentages_and_footnotes_are_stripped(self):
        items = parse("Aloe Barbadensis Juice*, Glycerin 5%")
        self.assertEqual([i.raw for i in items], ["Aloe Barbadensis Juice", "Glycerin"])

    def test_a_may_contain_block_is_marked_and_indexed_separately(self):
        items = parse("Aqua, Mica [+/- CI 77491, CI 77492]")
        positions = {i.raw: i.position for i in items}
        self.assertEqual(positions["Aqua"], "declared")
        self.assertEqual(positions["CI 77491"], "may-contain")
        self.assertEqual(
            [i.index for i in items if i.position == "may-contain"], [1, 2]
        )

    def test_a_bracketed_shade_block_ends_at_its_closing_bracket(self):
        items = parse("Aqua, Mica [+/- CI 77491, CI 77492], Talc")
        self.assertEqual(
            [(i.raw, i.position, i.index) for i in items],
            [
                ("Aqua", "declared", 1),
                ("Mica", "declared", 2),
                ("CI 77491", "may-contain", 1),
                ("CI 77492", "may-contain", 2),
                ("Talc", "declared", 3),
            ],
        )

    def test_html_entities_are_resolved_before_splitting(self):
        # The semicolon inside "&lt;" is a separator. Unescaping afterwards
        # left three ingredients called "&lt" on one real Russian pack and
        # three called "FD" on an American one, each reported as a repeat.
        items = parse("Aqua, &lt; 5 % soda, FD&amp;C Red 40")
        raws = [i.raw for i in items]
        self.assertNotIn("&lt", raws)
        self.assertNotIn("FD&amp", raws)
        self.assertIn("FD&C Red 40", raws)

    def test_punctuation_alone_is_not_an_ingredient(self):
        self.assertEqual(parse("Aqua, , -, ., Glycerin"), parse("Aqua, Glycerin"))


class SynonymsPrintedBesideAName(unittest.TestCase):
    def test_a_slash_with_a_space_separates_two_names_for_one_thing(self):
        item = parse("CI 77891 / TITANIUM DIOXIDE")[0]
        self.assertIn(("CI 77891", "part"), item.aliases)
        self.assertIn(("TITANIUM DIOXIDE", "part"), item.aliases)

    def test_a_slash_without_a_space_is_part_of_one_name(self):
        item = parse("Caprylic/Capric Triglyceride")[0]
        self.assertEqual(item.aliases, ())

    def test_a_slash_with_a_space_on_one_side_only_is_not_a_synonym(self):
        # "STYRENE/ ACRYLATES COPOLYMER" is a typesetting artefact. Splitting
        # it gave the fragment "STYRENE", which matches the styrene monomer in
        # Annex II, on 35 real labels.
        for printed in (
            "STYRENE/ ACRYLATES COPOLYMER",
            "Styrene /Acrylates Copolymer",
        ):
            with self.subTest(printed=printed):
                self.assertEqual(parse(printed)[0].aliases, ())

    def test_a_polymer_names_its_monomers_with_slashes_not_synonyms(self):
        for printed in (
            "Styrene / Acrylates Copolymer",
            "Acrylates / C10-30 Alkyl Acrylate Crosspolymer",
            "VP / VA Copolymer",
        ):
            with self.subTest(printed=printed):
                self.assertEqual(parse(printed)[0].aliases, ())

    def test_a_parenthetical_is_looked_up_separately(self):
        item = parse("Titanium Dioxide (CI 77891)")[0]
        self.assertIn(("CI 77891", "part"), item.aliases)
        self.assertIn(("Titanium Dioxide", "whole"), item.aliases)


class WhenTheFieldIsNotOneList(unittest.TestCase):
    def test_a_component_heading_is_found(self):
        self.assertEqual(
            component_headings("MASQUE: Aqua, Glycerin. GEL DOUCHE: Aqua, Parfum"),
            ["MASQUE", "GEL DOUCHE"],
        )

    def test_the_word_ingredients_alone_is_not_a_component(self):
        self.assertEqual(component_headings("Ingredients: Aqua, Glycerin"), [])

    def test_but_two_of_them_are_two_lists(self):
        headings = component_headings(
            "Ingredients: Aqua, Glycerin. Ingredients: Aqua, Parfum"
        )
        self.assertEqual(len(headings), 1)
        self.assertIn("appearing 2 times", headings[0])

    def test_a_warning_panel_heading_is_not_a_component(self):
        self.assertEqual(
            component_headings("Aqua, Glycerin. Caution: avoid the eyes."), []
        )

    def test_an_ordinary_list_has_none(self):
        self.assertEqual(component_headings("Aqua, Glycerin, Parfum, CI 77491"), [])


class RecognisingWhatIsNotAnIngredient(unittest.TestCase):
    def test_a_sentence_is_recognised_as_prose(self):
        item = parse(
            "Aqua, this rinse is not intended to replace brushing or flossing"
        )[1]
        self.assertTrue(looks_like_prose(item))

    def test_the_longest_real_inci_names_are_not(self):
        for name in (
            "Ammonium Polyacryldimethyltauramide / Ammonium Polyacryloyldimethyl "
            "Taurate",
            "Butyrospermum Parkii (Shea) Butter",
            "Hydrogenated Styrene/Methyl Styrene/Indene Copolymer",
            "PEG/PPG/Polybutylene Glycol-8/5/3 Glycerin",
        ):
            with self.subTest(name=name):
                self.assertFalse(looks_like_prose(parse(name)[0]))

    def test_bytes_are_not_a_list(self):
        self.assertTrue(looks_binary("PK\x03\x04\x00\x00" + "\x00" * 100))
        self.assertFalse(looks_binary("Aqua, Glycerin, Parfum"))
        self.assertFalse(looks_binary(""))


if __name__ == "__main__":
    unittest.main()


class HostileInput(unittest.TestCase):
    """Things that are not ingredient lists, and must not hang or raise.

    A checking tool that crashes on a bad file is annoying; one that takes
    twenty seconds on a pathological one will be killed by whatever is running
    it, and the run will look like a pass.
    """

    CASES = {
        "empty": "",
        "one comma": ",",
        "an unbroken 40,000-character run": "a" * 40_000,
        "8,000 entries": "aqua," * 8_000,
        "500 nested brackets": "(" * 500 + "aqua" + ")" * 500,
        "unbalanced open brackets": "aqua (" * 2_000,
        "unbalanced close brackets": "aqua )" * 2_000,
        "only a shade-range marker": "[+/- ]",
        "CRLF": "Aqua,\r\nGlycerin,\r\nParfum",
        "one giant parenthetical": "(" + "aqua, " * 5_000 + ")",
        "NUL bytes": "\x00" * 100,
        "control characters": "".join(chr(i) for i in range(1, 32)) * 100,
        "3,000 slash-separated names": " / ".join(["aqua"] * 3_000),
        "3,000 colons": "a: " * 3_000,
        "nested shade-range markers": "[+/- [+/- [+/- CI 77491]]]",
    }

    def test_none_of_them_raises(self):
        for name, text in self.CASES.items():
            with self.subTest(case=name):
                parse(text)
                trim(text)
                component_headings(text)

    def test_a_whole_analysis_survives_each_of_them_quickly(self):
        """The parser is not the whole tool.

        This class was written to catch "twenty seconds on a pathological
        input" and for a while it only exercised the parser, so a quadratic
        loop in the position check -- 64 seconds on 20,000 colour index
        numbers -- lived underneath it.
        """
        import time

        from on_the_list.analyse import analyse
        from on_the_list.register import load

        register = load()
        cases = dict(self.CASES)
        cases["20,000 colour index numbers"] = ", ".join(
            f"CI {10000 + i % 50000}" for i in range(20_000)
        )
        cases["20,000 repeated names"] = ", ".join(["aqua"] * 20_000)
        for name, text in cases.items():
            with self.subTest(case=name):
                start = time.perf_counter()
                analyse(
                    ingredients_text=text,
                    label_text=text,
                    pack_text=text,
                    register=register,
                )
                self.assertLess(time.perf_counter() - start, 5.0, name)

    def test_building_aliases_is_not_quadratic(self):
        # A single entry holding 3,000 slash-separated names took 2.4 seconds,
        # because every comparison re-folded the whole string. Ten thousand of
        # them is the guard: on the quadratic version it would take minutes.
        import time

        start = time.perf_counter()
        parse(" / ".join(["aqua"] * 10_000))
        self.assertLess(time.perf_counter() - start, 5.0)


class DefectsFoundByReview(unittest.TestCase):
    """Each of these produced a wrong answer with no error and no warning."""

    def test_a_leading_ingredients_heading_is_not_part_of_the_first_name(self):
        # A file handed to --ingredients is usually copied straight off a pack
        # and starts with the word. Without stripping it the first ingredient
        # became "Ingredients: Formaldehyde", matched nothing, and the run
        # exited 0 -- while the same text through the whole-label path reported
        # the prohibited match.
        block, _ = trim("Ingredients: Formaldehyde, Aqua, Glycerin")
        self.assertEqual(
            [i.raw for i in parse(block)], ["Formaldehyde", "Aqua", "Glycerin"]
        )
        for heading in ("INCI:", "Ingrédients:", "Ingredientes -"):
            with self.subTest(heading=heading):
                block, _ = trim(f"{heading} Formaldehyde, Aqua")
                self.assertEqual(parse(block)[0].raw, "Formaldehyde")

    def test_a_bracket_holding_most_of_the_name_leaves_a_fragment(self):
        # "Citrus Limon (Lemon) Peel Oil" keeps four words of five and is still
        # the name. "Styrene (Acrylate Copolymer)" keeps one of three and is a
        # fragment, which matched the styrene monomer in Annex II.
        self.assertIn(
            ("Citrus Limon Peel Oil", "whole"),
            parse("Citrus Limon (Lemon) Peel Oil")[0].aliases,
        )
        self.assertIn(
            ("Titanium Dioxide", "whole"),
            parse("Titanium Dioxide (nano)")[0].aliases,
        )
        self.assertIn(
            ("Styrene", "part"), parse("Styrene (Acrylate Copolymer)")[0].aliases
        )

    def test_the_same_substance_gets_the_same_answer_either_way_round(self):
        # "Chromium (CI 77288)" was reported as prohibited and
        # "CI 77288 / CHROMIUM" was not. Same substance, two print orders.
        for printed in ("Chromium (CI 77288)", "CI 77288 / CHROMIUM"):
            with self.subTest(printed=printed):
                kinds = {kind for _, kind in parse(printed)[0].aliases}
                self.assertEqual(kinds, {"part"})

    def test_a_tolerance_does_not_open_a_shade_range_block(self):
        # "Glycerin +/- 0.5%" and "pH 5.5 +/- 0.5" are ordinary label text.
        # Reading either as a shade-range marker moved every declared entry
        # after it out of both order-dependent checks, and the only thing the
        # report said was that the list "has a 'may contain' block".
        for text in (
            "Aqua, Glycerin +/- 0.5%, Parfum, CI 77491",
            "Aqua, Glycerin, pH 5.5 ± 0.5, Parfum",
        ):
            with self.subTest(text=text):
                items = parse(text)
                self.assertTrue(all(i.position == "declared" for i in items))

    def test_but_a_real_shade_range_block_still_opens_one(self):
        for text in (
            "Aqua, Mica [+/- CI 77491, CI 77492]",
            "Aqua, Mica +/- CI 77491, CI 77492",
            "Aqua, Mica, May Contain: CI 77491",
        ):
            with self.subTest(text=text):
                items = parse(text)
                self.assertTrue(any(i.position == "may-contain" for i in items))

    def test_a_contains_statement_only_ends_the_list_at_a_sentence(self):
        # "Contains Nothing Extract 2%" mid-list used to truncate the list and
        # lose every ingredient after it, including a prohibited one.
        kept, dropped = trim(
            "Aqua, Glycerin, Contains Nothing Extract 2%, "
            "Butylphenyl Methylpropional"
        )
        self.assertIn("Butylphenyl Methylpropional", kept)
        self.assertEqual(dropped, "")

    def test_a_content_declaration_after_a_full_stop_still_ends_it(self):
        kept, dropped = trim(
            "Aqua, CI 77891. Contient du fluorure de sodium (1450 ppm de fluor)"
        )
        self.assertNotIn("fluorure", kept)
        self.assertIn("fluorure", dropped)

    def test_replacement_characters_are_not_printable_text(self):
        # A non-UTF-8 binary with no NUL bytes arrives as U+FFFD after
        # errors="replace", and str.isprintable() says every one is printable.
        self.assertTrue(looks_binary(bytes(range(128, 256)).decode("utf-8", "replace") * 40))
