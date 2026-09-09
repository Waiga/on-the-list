"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from on_the_list import __version__
from on_the_list import register as register_mod
from on_the_list import report as report_mod
from on_the_list.analyse import analyse
from on_the_list.checks import CHECKS

# 0  the checks that ran found nothing
# 1  at least one finding
# 2  the run could not be carried out: unreadable input, no ingredient list,
#    or a register that would not load. Exiting 0 there would let a job go
#    green over a label nothing was compared to, which is the one thing this
#    tool exists not to do.
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

SUBCOMMANDS = ("update-register", "register")


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    # Label text is copied out of PDFs, spreadsheets and web pages and arrives
    # with whatever encoding that produced. Refusing to open it is worse than
    # reading it imperfectly and saying so.
    return Path(path).read_text(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="on-the-list",
        description=(
            "Read a cosmetic ingredient list and report what Annexes II to VI "
            "of Regulation (EC) No 1223/2009 say about the ingredients on it. "
            "Runs entirely on your machine; the register is downloaded once, "
            "by a separate command."
        ),
        epilog=(
            "Subcommands: update-register (download a fresh register), "
            "register (say which register is in use). "
            "Exit codes: 0 nothing found, 1 at least one finding, 2 could not "
            "run."
        ),
    )
    parser.add_argument(
        "label",
        nargs="?",
        help=(
            "File holding the label text, or - for standard input. It may "
            "hold the whole pack: the ingredient list is located inside it."
        ),
    )
    parser.add_argument(
        "--ingredients",
        metavar="FILE",
        help="File holding only the ingredient list, or - for stdin.",
    )
    parser.add_argument(
        "--pack-text",
        metavar="FILE",
        help=(
            "File holding everything printed on the pack. Required by the "
            "warning-wording check, which does not run without it."
        ),
    )
    parser.add_argument(
        "--register",
        metavar="DIR",
        help=(
            "Read the annex CSVs from this directory instead of the copy "
            "shipped with the package."
        ),
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=sorted(CHECKS),
        metavar="CHECK",
        help="Switch off one check. Repeat to switch off more.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="Print every check this tool runs, and exit.",
    )
    parser.add_argument(
        "--version", action="version", version=f"on-the-list {__version__}"
    )
    return parser


def _update_register(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="on-the-list update-register",
        description=(
            "Download Annexes II to VI from the European Commission's CosIng "
            "API and keep them for later runs. This is the only command that "
            "uses the network."
        ),
    )
    parser.add_argument(
        "--into",
        metavar="DIR",
        help="Where to write them. Default: this platform's user data "
        "directory for on-the-list.",
    )
    args = parser.parse_args(argv)

    from on_the_list import fetch  # imported here, and only here
    from on_the_list.paths import register_dir

    destination = Path(args.into) if args.into else register_dir()
    try:
        lines = fetch.update(destination)
    except fetch.FetchError as exc:
        sys.stderr.write(f"on-the-list: could not download the register: {exc}\n")
        return EXIT_ERROR
    except OSError as exc:
        sys.stderr.write(f"on-the-list: could not write the register: {exc}\n")
        return EXIT_ERROR
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _show_register(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="on-the-list register",
        description="Say exactly which register is in use, and its hashes.",
    )
    parser.add_argument("--register", metavar="DIR")
    args = parser.parse_args(argv)
    try:
        register = register_mod.load(args.register)
    except register_mod.RegisterError as exc:
        sys.stderr.write(f"on-the-list: {exc}\n")
        return EXIT_ERROR
    sys.stdout.write("\n".join(register_mod.describe(register)) + "\n")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in SUBCOMMANDS:
        if argv[0] == "update-register":
            return _update_register(argv[1:])
        return _show_register(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        sys.stdout.write(report_mod.render_checks())
        return EXIT_OK

    if not args.label and not args.ingredients:
        parser.error(
            "nothing to read: pass a label file, - for standard input, or "
            "--ingredients"
        )
    if args.label and args.ingredients:
        parser.error("give either a label file or --ingredients, not both")
    if [args.label, args.ingredients, args.pack_text].count("-") > 1:
        parser.error("standard input can only be read once")

    try:
        register = register_mod.load(args.register)
    except register_mod.RegisterError as exc:
        sys.stderr.write(f"on-the-list: {exc}\n")
        return EXIT_ERROR

    try:
        label_text = _read(args.label) if args.label else ""
        ingredients_text = _read(args.ingredients) if args.ingredients else ""
        pack_text = _read(args.pack_text) if args.pack_text else ""
    except OSError as exc:
        sys.stderr.write(f"on-the-list: cannot read input: {exc}\n")
        return EXIT_ERROR

    source = args.label or args.ingredients or ""
    if source == "-":
        source = "standard input"

    result = analyse(
        label_text=label_text,
        ingredients_text=ingredients_text,
        pack_text=pack_text,
        register=register,
        source=source,
        skip=frozenset(args.skip),
    )

    renderers = {
        "text": report_mod.render_text,
        "markdown": report_mod.render_markdown,
        "json": report_mod.render_json,
    }
    output = renderers[args.format](result)
    # A label may legitimately contain characters the terminal encoding cannot
    # represent. Losing a character is acceptable; failing the run over it is
    # not.
    sys.stdout.buffer.write(
        output.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace")
    )

    if not result.parsed:
        return EXIT_ERROR
    if result.findings:
        return EXIT_FINDINGS
    return EXIT_OK
