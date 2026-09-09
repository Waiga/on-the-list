"""Download the annexes. The only module in this package that touches a network.

It is deliberately quarantined. Nothing on the analysis path imports it -- not
``analyse``, not ``checks``, not ``register`` -- and ``tests/test_offline.py``
proves that by reading the import graph rather than by taking this docstring's
word for it. The command line reaches it through a function-local import inside
``update-register`` and nowhere else.

Downloading is therefore something a user asks for once, out loud, by name. It
never happens as a side effect of analysing a label.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path

from on_the_list import __version__
from on_the_list import registry_manifest as manifest

#: Sent so that the Commission can see what is calling, which is ordinary
#: courtesy towards a public API with no key and no rate limit published.
USER_AGENT = (
    f"on-the-list/{__version__} "
    "(+https://github.com/Waiga/on-the-list) python-urllib"
)

TIMEOUT = 60


class FetchError(Exception):
    """The download did not complete, and nothing was written."""


def download_annex(annex: str, *, timeout: int = TIMEOUT) -> bytes:
    """Fetch one annex CSV and return its bytes."""
    url = manifest.SOURCE_URL.format(annex=annex)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise FetchError(f"{url}: {exc}") from exc
    except OSError as exc:  # pragma: no cover - network shapes vary
        raise FetchError(f"{url}: {exc}") from exc

    head = payload[:200].decode("utf-8", errors="replace")
    if "File creation date" not in head:
        raise FetchError(
            f"{url} returned {len(payload)} bytes that do not look like an "
            "annex export. The first line was:\n  " + head.splitlines()[0][:120]
        )
    return payload


def update(destination: Path, *, timeout: int = TIMEOUT) -> list[str]:
    """Download all five annexes into ``destination``.

    Every file is fetched and checked before anything is written, so a failure
    part way through leaves the previous register intact rather than half
    replaced. Returns the report lines to print.
    """
    payloads: dict[str, bytes] = {}
    for annex in manifest.ORDER:
        payloads[annex] = download_annex(annex, timeout=timeout)

    destination.mkdir(parents=True, exist_ok=True)
    lines = [f"Register written to {destination}", ""]
    for annex in manifest.ORDER:
        payload = payloads[annex]
        record = manifest.ANNEXES[annex]
        path = destination / str(record["filename"])
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        same = " (same as the copy shipped with this package)" if (
            digest == record["sha256"]
        ) else ""
        lines.append(f"Annex {annex}  {len(payload):>8} bytes")
        lines.append(f"  sha256 {digest}{same}")
    lines.append("")
    lines.append(manifest.SOURCE_ATTRIBUTION)
    return lines
