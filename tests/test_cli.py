"""The command line, including the exit codes a CI job depends on."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from on_the_list import __version__
from on_the_list.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main


class Runner:
    """Run the CLI and capture what it wrote, without spawning anything."""

    def __init__(self, *argv: str):
        out = io.StringIO()
        out.buffer = io.BytesIO()  # type: ignore[attr-defined]
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.code = main(list(argv))
        self.stdout = out.buffer.getvalue().decode("utf-8", "replace")  # type: ignore[attr-defined]
        self.stdout += out.getvalue()
        self.stderr = err.getvalue()


def write(directory: Path, name: str, text: str) -> str:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return str(path)


class ExitCodes(unittest.TestCase):
    """0 nothing found, 1 at least one finding, 2 could not run.

    The third one matters most. A job that goes green over a label nothing was
    compared to is the one thing this tool exists not to do.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nothing_found(self):
        path = write(self.dir, "clean.txt", "Ingredients: Aqua, Glycerin, Parfum.")
        self.assertEqual(Runner(path).code, EXIT_OK)

    def test_a_finding(self):
        path = write(
            self.dir, "found.txt", "Ingredients: Aqua, Butylphenyl Methylpropional."
        )
        self.assertEqual(Runner(path).code, EXIT_FINDINGS)

    def test_no_ingredient_list_is_an_error_not_a_pass(self):
        path = write(self.dir, "copy.txt", "A rich cream for dry skin.")
        result = Runner(path)
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("No ingredient list was found", result.stdout)

    def test_an_unreadable_file(self):
        result = Runner(str(self.dir / "missing.txt"))
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("cannot read input", result.stderr)

    def test_switching_off_every_check_is_not_a_pass(self):
        # "Nothing found" would be a lie about a comparison that never
        # happened, and in a CI job a green tick over a label with an Annex II
        # substance printed first.
        path = write(
            self.dir, "l.txt", "Ingredients: Aqua, Butylphenyl Methylpropional."
        )
        result = Runner(
            path, "--skip", "prohibited", "--skip", "colourant-order",
            "--skip", "repeated-entry", "--skip", "warning-wording",
        )
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("every check was switched off", result.stderr)

    def test_a_malformed_register_is_an_error_not_a_traceback(self):
        # Exit 1 is EXIT_FINDINGS, and the carefully worded message about the
        # export format having changed was never reached.
        path = write(self.dir, "l.txt", "Ingredients: Aqua, Glycerin.")
        bad = self.dir / "bad"
        bad.mkdir()
        for annex in ("II", "III", "IV", "V", "VI"):
            (bad / f"annex_{annex}.csv").write_text(
                "a\nb\nc\nd\nnot,the,header\n1,2\n", encoding="utf-8"
            )
        result = Runner(path, "--register", str(bad))
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("export format", result.stderr)

    def test_a_register_of_bytes_is_an_error_not_a_traceback(self):
        path = write(self.dir, "l.txt", "Ingredients: Aqua, Glycerin.")
        bad = self.dir / "bytes"
        bad.mkdir()
        for annex in ("II", "III", "IV", "V", "VI"):
            (bad / f"annex_{annex}.csv").write_bytes(b"\xff\xfe\x00\x01" * 50)
        result = Runner(path, "--register", str(bad))
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("not UTF-8", result.stderr)

    def test_the_reason_a_check_did_not_run_is_the_right_reason(self):
        # With no ingredient list, warning-wording kept "no pack text was
        # supplied ... Pass --pack-text to run it." on a run where --pack-text
        # had been supplied. The report told the reader to do what they had
        # just done.
        label = write(self.dir, "copy.txt", "A rich cream for dry skin.")
        pack = write(self.dir, "pack.txt", "Contains sodium fluoride")
        result = Runner(label, "--pack-text", pack)
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertNotIn("no pack text was supplied", result.stdout)
        self.assertEqual(result.stdout.count("there was no ingredient list"), 4)

    def test_a_register_directory_that_holds_no_register(self):
        path = write(self.dir, "clean.txt", "Ingredients: Aqua, Glycerin.")
        empty = self.dir / "empty"
        empty.mkdir()
        result = Runner(path, "--register", str(empty))
        self.assertEqual(result.code, EXIT_ERROR)
        self.assertIn("update-register", result.stderr)


class OutputFormats(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = write(
            Path(self.tmp.name),
            "label.txt",
            "Ingredients: Aqua, Petrolatum, CI 77491, Glycerin, Glycerin.",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_names_the_register_version(self):
        out = Runner(self.path).stdout
        self.assertIn("28/08/2026", out)
        self.assertIn("CHECKS", out)
        self.assertIn("COVERAGE", out)

    def test_text_carries_the_disclaimer(self):
        out = Runner(self.path).stdout
        self.assertIn("Nothing here is a statement that this product is", out)

    def test_markdown(self):
        out = Runner(self.path, "--format", "markdown").stdout
        self.assertTrue(out.startswith("# on-the-list"))
        self.assertIn("## Checks", out)
        # str.title() would render this "Annex Ii".
        self.assertIn("## Names that match an Annex II entry", out)

    def test_json_is_valid_and_names_its_register(self):
        payload = json.loads(Runner(self.path, "--format", "json").stdout)
        self.assertEqual(payload["version"], __version__)
        self.assertTrue(payload["ingredient_list_parsed"])
        self.assertEqual(len(payload["register"]["annexes"]), 5)
        self.assertIn("sha256", payload["register"]["annexes"]["II"])
        self.assertIn("not a statement about compliance", payload["disclaimer"])

    def test_json_keeps_absence_and_findings_apart(self):
        payload = json.loads(Runner(self.path, "--format", "json").stdout)
        self.assertIn("not_restricted_by_these_annexes", payload)
        self.assertIn("Aqua", payload["not_restricted_by_these_annexes"])
        self.assertNotIn("unknown", json.dumps(payload).lower())


class Arguments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_checks(self):
        result = Runner("--list-checks")
        self.assertEqual(result.code, EXIT_OK)
        for name in (
            "prohibited", "colourant-order", "repeated-entry", "warning-wording"
        ):
            self.assertIn(name, result.stdout)

    def test_ingredients_and_pack_text_together(self):
        ingredients = write(self.dir, "inci.txt", "Aqua, Sorbitol, Sodium Fluoride")
        pack = write(self.dir, "pack.txt", "Mint toothpaste, 75 ml")
        result = Runner("--ingredients", ingredients, "--pack-text", pack)
        self.assertEqual(result.code, EXIT_FINDINGS)
        self.assertIn("Contains sodium fluoride", result.stdout)

    def test_skip(self):
        path = write(
            self.dir, "l.txt", "Ingredients: Aqua, Butylphenyl Methylpropional."
        )
        result = Runner(path, "--skip", "prohibited")
        self.assertEqual(result.code, EXIT_OK)
        self.assertIn("not run  prohibited", result.stdout)

    def test_stdin(self):
        original = sys.stdin
        sys.stdin = io.StringIO("Ingredients: Aqua, Glycerin, Parfum.")
        try:
            self.assertEqual(Runner("-").code, EXIT_OK)
        finally:
            sys.stdin = original

    def test_both_a_label_and_ingredients_is_refused(self):
        path = write(self.dir, "l.txt", "Ingredients: Aqua")
        with self.assertRaises(SystemExit):
            Runner(path, "--ingredients", path)

    def test_nothing_at_all_is_refused(self):
        with self.assertRaises(SystemExit):
            Runner()


class Subcommands(unittest.TestCase):
    def test_register_prints_the_hashes_and_the_attribution(self):
        result = Runner("register")
        self.assertEqual(result.code, EXIT_OK)
        self.assertIn("European Union", result.stdout)
        self.assertIn(
            "b7105a05bf724bb10cebaac3a3813b6146c3153ae1d07097d35bb1f73cd7283b",
            result.stdout,
        )
        self.assertIn("api.tech.ec.europa.eu", result.stdout)

    def test_analysing_a_label_never_loads_the_network_module(self):
        """The quarantine, checked by running rather than by reading.

        The previous version of this test asserted that the string
        "update-register" was in a tuple of subcommand names, which is a
        constant, and its comment claimed it checked the network path.
        """
        import sys

        for name in [n for n in sys.modules if n == "on_the_list.fetch"]:
            del sys.modules[name]
        with tempfile.TemporaryDirectory() as directory:
            path = write(
                Path(directory), "l.txt", "Ingredients: Aqua, Formaldehyde."
            )
            for argv in ([path], [path, "--format", "json"], ["--list-checks"]):
                Runner(*argv)
                self.assertNotIn("on_the_list.fetch", sys.modules)
        # And the command that does reach out is reached only by its own name.
        from on_the_list import cli

        self.assertEqual(cli.SUBCOMMANDS, ("update-register", "register"))


if __name__ == "__main__":
    unittest.main()
