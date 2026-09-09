"""The promise that analysis never touches the network, enforced as a test.

The claim is narrow and it has to stay narrow to be worth anything: reading a
label and reporting what the annexes say about it opens no connection and
starts no process. Downloading a register does, obviously, and that is a
separate command in a separate module.

So this file checks four different things, because none of them alone is
enough:

* every module on the analysis path is read as source and refused if it can
  reach out -- an allowlist of imports, the process-starting parts of ``os``,
  and the dynamic escape hatches that would let either in without an import;
* ``fetch`` is imported nowhere at module level, so importing the package or
  running an analysis cannot pull it in;
* an analysis actually runs with ``socket.socket`` replaced by something that
  raises, which catches anything the static read models wrongly;
* nothing but Python source and the declared annex CSVs exists in the package,
  and each of those CSVs still hashes to what the manifest says.

The structure of the AST check follows ``follow-through``'s, a sibling tool,
including its hard-won conclusion that an allowlist is the only thing that
works: two denylists there let ``_socket``, ``_posixsubprocess``,
``concurrent.futures`` and ``logging.handlers`` through.

Every detector has a test proving it can fail. A guard nobody has seen fail is
not a guard.
"""

from __future__ import annotations

import ast
import hashlib
import socket
import tempfile
import unittest
from pathlib import Path

import on_the_list
from on_the_list import registry_manifest as manifest
from on_the_list.analyse import analyse
from on_the_list.register import load

PACKAGE = Path(on_the_list.__file__).parent

#: The one module allowed to reach out. It is not on the analysis path and the
#: tests below prove nothing imports it at module level.
NETWORK_MODULE = "fetch.py"

#: The only modules the analysis path may import.
ALLOWED_MODULES = frozenset(
    {
        "__future__", "argparse", "csv", "dataclasses", "hashlib", "html", "io",
        "json", "os", "pathlib", "re", "sys", "typing", "unicodedata",
        "on_the_list",
    }
)

#: ``os`` is allowed, because finding a platform data directory needs it.
#: These are not. Checked by name wherever they appear, so ``import os as o;
#: o.popen(...)`` and ``from os import popen`` are caught as well as
#: ``os.popen(...)``.
FORBIDDEN_OS_CALLS = frozenset(
    {
        "execl", "execle", "execlp", "execv", "execve", "execvp", "execvpe",
        "fork", "forkpty", "popen", "posix_spawn", "posix_spawnp", "spawnl",
        "spawnle", "spawnlp", "spawnv", "spawnve", "spawnvp", "spawnvpe",
        "startfile", "system",
    }
)

#: Ways to reach a forbidden capability without naming it in an import.
FORBIDDEN_NAMES = frozenset(
    {
        "__builtins__", "__import__", "builtins", "eval", "exec", "getattr",
        "globals", "importlib", "locals", "modules", "vars",
    }
)

#: Still dangerous written as an attribute. ``compile`` is deliberately absent:
#: ``re.compile`` builds every pattern in this package.
FORBIDDEN_ATTRIBUTES = FORBIDDEN_OS_CALLS | {
    "__builtins__", "__dict__", "__getattribute__", "__globals__",
    "__import__", "__subclasses__", "eval", "exec", "modules",
}


def analysis_modules() -> list[Path]:
    """Every Python file in the package except the one network module."""
    return sorted(
        path for path in PACKAGE.rglob("*.py") if path.name != NETWORK_MODULE
    )


def offences(source: str, filename: str = "<source>") -> set[str]:
    """Everything in ``source`` that would break the offline promise.

    Names are checked wherever they appear rather than in the one shape they
    are usually written, because ``import os as o`` and ``from os import
    popen`` both walk past a check that looks for an attribute of a variable
    literally called ``os``.
    """
    tree = ast.parse(source, filename=filename)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_MODULES:
                    found.add(f"import {root}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level == 0 and root not in ALLOWED_MODULES:
                found.add(f"from {root} import ...")
            for alias in node.names:
                if alias.name == "*":
                    found.add(f"from {node.module} import *")
                elif (
                    alias.name in FORBIDDEN_OS_CALLS
                    or alias.name in FORBIDDEN_NAMES
                ):
                    found.add(f"from {node.module} import {alias.name}")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                found.add(f".{node.attr}")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_OS_CALLS or node.id in FORBIDDEN_NAMES:
                found.add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # getattr(os, "popen") hides the name in a string.
            if node.value in FORBIDDEN_OS_CALLS:
                found.add(f"literal {node.value!r}")
    return found


class NothingOnTheAnalysisPathCanReachOut(unittest.TestCase):
    def test_there_are_modules_to_check(self):
        self.assertGreater(len(analysis_modules()), 6)

    def test_the_scan_covers_the_modules_that_matter(self):
        names = {path.name for path in analysis_modules()}
        for expected in (
            "analyse.py", "annexes.py", "checks.py", "cli.py",
            "ingredients.py", "normalise.py", "register.py", "report.py",
        ):
            self.assertIn(expected, names)

    def test_no_analysis_module_can_reach_out(self):
        for module in analysis_modules():
            with self.subTest(module=module.name):
                found = offences(module.read_text(encoding="utf-8"), str(module))
                self.assertEqual(found, set(), f"{module.name}: {sorted(found)}")


class TheNetworkModuleIsQuarantined(unittest.TestCase):
    """``fetch`` exists, and nothing on the analysis path can pull it in."""

    def test_it_exists_and_is_the_one_module_that_reaches_out(self):
        source = (PACKAGE / NETWORK_MODULE).read_text(encoding="utf-8")
        self.assertIn("import urllib", source)
        self.assertNotEqual(offences(source), set())

    def test_no_module_imports_it_at_module_level(self):
        """A module-level import would make ``import on_the_list`` load it.

        The command line reaches it from inside the ``update-register``
        function and nowhere else, which is what keeps analysing a label from
        being able to open a connection even by accident.
        """
        for module in analysis_modules():
            tree = ast.parse(module.read_text(encoding="utf-8"), str(module))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                names = [alias.name for alias in node.names]
                text = (getattr(node, "module", "") or "") + " " + " ".join(names)
                if "fetch" not in text:
                    continue
                # It may only appear inside a function body.
                enclosing = [
                    parent
                    for parent in ast.walk(tree)
                    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and any(child is node for child in ast.walk(parent))
                ]
                self.assertTrue(
                    enclosing,
                    f"{module.name} imports fetch at module level",
                )

    def test_importing_the_package_does_not_load_it(self):
        import sys

        for name in list(sys.modules):
            if name == "on_the_list.fetch":
                del sys.modules[name]
        import importlib  # noqa: F401 - the test itself may import freely

        importlib.reload(on_the_list)
        self.assertNotIn("on_the_list.fetch", sys.modules)


class AnAnalysisRunsWithTheNetworkTakenAway(unittest.TestCase):
    """The static read is a model. This runs the real thing with sockets gone."""

    LABEL = (
        "Ingredients: Aqua, Glycerin, Methylparaben, Formaldehyde, "
        "CI 77491, Cetearyl Alcohol, Glycerin."
    )

    def test_a_full_analysis_completes_with_socket_disabled(self):
        original = socket.socket

        def refuse(*args, **kwargs):
            raise AssertionError("analysis opened a socket")

        socket.socket = refuse  # type: ignore[assignment]
        try:
            register = load()
            report = analyse(
                label_text=self.LABEL, register=register, source="test"
            )
        finally:
            socket.socket = original  # type: ignore[assignment]

        self.assertTrue(report.parsed)
        self.assertTrue(report.findings)


class ThePackageHoldsOnlySourceAndTheDeclaredRegister(unittest.TestCase):
    def test_no_stray_files(self):
        """Everything importable must be something the scan above can read.

        A compiled extension or a sourceless ``.pyc`` in the package is just as
        importable and has no source to parse, so it would pass unexamined.
        Rather than trying to inspect a binary, refuse to have one.
        """
        strays = [
            path
            for path in PACKAGE.rglob("*")
            if path.is_file()
            and path.suffix != ".py"
            and "__pycache__" not in path.parts
            and path.name not in manifest.DECLARED_DATA_FILES
        ]
        self.assertEqual(
            strays, [], f"undeclared files: {[str(p) for p in strays]}"
        )

    def test_every_declared_file_is_present_and_unchanged(self):
        for annex, record in manifest.ANNEXES.items():
            with self.subTest(annex=annex):
                path = PACKAGE / "data" / str(record["filename"])
                raw = path.read_bytes()
                self.assertEqual(len(raw), record["size"])
                self.assertEqual(
                    hashlib.sha256(raw).hexdigest(), record["sha256"]
                )

    def test_the_package_declares_no_dependencies(self):
        # The scan reads only this package. That is good enough only because
        # there is nothing else in the install to read.
        packaging = PACKAGE.parent / "pyproject.toml"
        if not packaging.is_file():  # installed copy, not a source checkout
            self.skipTest("pyproject.toml is not beside an installed package")
        self.assertIn("dependencies = []", packaging.read_text(encoding="utf-8"))


class TheGuardCanFail(unittest.TestCase):
    """Each detector, shown catching the thing it exists to catch."""

    def assert_caught(self, source: str, expected: str):
        self.assertIn(expected, offences(source))

    def test_catches_a_plain_import(self):
        self.assert_caught("import socket\n", "import socket")

    def test_catches_a_dotted_import(self):
        self.assert_caught("import urllib.request\n", "import urllib")

    def test_catches_a_from_import(self):
        self.assert_caught("from http import client\n", "from http import ...")

    def test_catches_a_process_launch_through_os(self):
        self.assert_caught("import os\nos.popen('curl example.com')\n", ".popen")

    def test_catches_a_process_launch_behind_an_alias(self):
        self.assert_caught("import os as o\no.popen('x')\n", ".popen")

    def test_catches_a_process_launch_imported_by_name(self):
        self.assert_caught("from os import system\n", "from os import system")

    def test_catches_the_name_hidden_in_a_string(self):
        self.assert_caught("import os\ngetattr(os, 'popen')('x')\n", "getattr")

    def test_catches_a_star_import(self):
        self.assert_caught("from urllib import *\n", "from urllib import *")

    def test_catches_the_spawn_family_completely(self):
        for call in ("spawnv", "spawnvpe", "posix_spawn", "forkpty"):
            with self.subTest(call=call):
                self.assert_caught(f"import os\nos.{call}()\n", f".{call}")

    def test_catches_the_private_accelerator_behind_a_banned_module(self):
        # `import socket` is obvious. `import _socket` is the same capability.
        for module in ("_socket", "_ssl", "_ctypes", "_posixsubprocess"):
            with self.subTest(module=module):
                self.assert_caught(f"import {module}\n", f"import {module}")

    def test_catches_the_polite_front_doors(self):
        self.assert_caught(
            "from concurrent.futures import ProcessPoolExecutor\n",
            "from concurrent import ...",
        )
        self.assert_caught(
            "from logging.handlers import HTTPHandler\n",
            "from logging import ...",
        )

    def test_catches_a_module_nobody_thought_to_ban(self):
        # The point of an allowlist: it does not need to have heard of it.
        for module in ("runpy", "pty", "venv", "doctest", "nt", "wsgiref"):
            with self.subTest(module=module):
                self.assert_caught(f"import {module}\n", f"import {module}")

    def test_catches_reaching_through_a_dunder(self):
        self.assert_caught("import os\nos.__dict__['system']('x')\n", ".__dict__")
        self.assert_caught(
            "import os\nos.__getattribute__('popen')('x')\n", ".__getattribute__"
        )

    def test_catches_the_module_table(self):
        self.assert_caught("import sys\nsys.modules['socket']\n", ".modules")

    def test_catches_the_dynamic_import_hatch(self):
        self.assert_caught("x = __import__('socket')\n", "__import__")
        self.assert_caught("import importlib\n", "import importlib")

    def test_catches_eval_and_exec(self):
        self.assert_caught("eval('1')\n", "eval")
        self.assert_caught("exec('pass')\n", "exec")

    def test_allows_what_this_package_actually_needs(self):
        source = (
            "import csv\nimport io\nimport re\nimport os\n"
            "re.compile('x')\nos.environ.get('HOME')\n"
        )
        self.assertEqual(offences(source), set())

    def test_a_real_smuggled_module_is_caught(self):
        source = (
            "import _socket\n"
            "from logging.handlers import SocketHandler\n"
            "\n"
            "def send(payload):\n"
            "    connection = _socket.socket()\n"
            "    connection.connect(('example.invalid', 80))\n"
        )
        found = offences(source)
        self.assertIn("import _socket", found)
        self.assertIn("from logging import ...", found)

    def test_the_scanner_reads_a_file_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "sample.py"
            sample.write_text("import socket\n", encoding="utf-8")
            self.assertIn(
                "import socket", offences(sample.read_text(encoding="utf-8"))
            )


class WhatThisDoesNotCover(unittest.TestCase):
    """The limits of this check, written down rather than left to be found.

    The static half is a read of one package's source. It is a guard against
    drift, not a sandbox: it cannot see what a dependency does, and there are
    none only because the package declares none. What remains uncovered by the
    static half is a name assembled at runtime -- ``"po" + "pen"`` -- since the
    string never appears in the source.

    The runtime half narrows that: an analysis is run with ``socket.socket``
    replaced, which a name assembled at runtime would still trip over. It does
    not cover a process launched to do the reaching, or a write to a path that
    something else is watching. Those are written down here rather than left
    for somebody to discover.
    """

    def test_this_docstring_is_the_test(self):
        self.assertTrue(WhatThisDoesNotCover.__doc__)


if __name__ == "__main__":
    unittest.main()
