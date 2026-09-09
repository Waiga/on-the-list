#!/usr/bin/env python3
"""Run on-the-list over an Open Beauty Facts export and report what happened.

This is the script behind every corpus number in the README. It is here so that
the measurement can be re-run rather than believed.

    curl -sO https://static.openbeautyfacts.org/data/en.openbeautyfacts.org.products.csv.gz
    shasum -a 256 en.openbeautyfacts.org.products.csv.gz
    python3 tools/measure_corpus.py en.openbeautyfacts.org.products.csv.gz

The export is Open Database Licence 1.0, which is share-alike and therefore
incompatible with redistributing a filtered subset inside an MIT repository. It
is not vendored here. Only the measurements are published, and the hash above
is how you check you have the same file.

Selection rule, applied to every record in the export: keep it if its
``ingredients_text`` field is at least 50 characters. Nothing else is filtered,
sorted or sampled.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from on_the_list.analyse import analyse  # noqa: E402
from on_the_list.register import load  # noqa: E402

MIN_INGREDIENTS_CHARS = 50


def records(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        for row in reader:
            yield dict(zip(header, row))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--samples", type=Path, help="write a sample of findings here")
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()

    digest = hashlib.sha256(args.export.read_bytes()).hexdigest()
    register = load()

    csv.field_size_limit(10**8)
    total = kept = crashes = 0
    parsed = 0
    ingredient_count = 0
    per_check = Counter()
    labels_with = Counter()
    samples: dict[str, list] = {}
    started = time.time()

    for record in records(args.export):
        total += 1
        text = record.get("ingredients_text") or ""
        if len(text) < MIN_INGREDIENTS_CHARS:
            continue
        kept += 1
        try:
            report = analyse(
                ingredients_text=text,
                pack_text=" ".join(
                    filter(
                        None,
                        (
                            record.get("product_name") or "",
                            record.get("generic_name") or "",
                        ),
                    )
                ),
                register=register,
                source=record.get("code") or "",
            )
        except Exception as exc:  # noqa: BLE001 - the point is to count these
            crashes += 1
            samples.setdefault("crash", []).append(
                {"code": record.get("code"), "error": repr(exc)}
            )
            continue
        if report.parsed:
            parsed += 1
        ingredient_count += len(report.ingredients)
        seen = set()
        for finding in report.findings:
            per_check[finding.check] += 1
            seen.add(finding.check)
            samples.setdefault(finding.check, []).append(
                {
                    "code": record.get("code"),
                    "summary": finding.summary,
                    "detail": list(finding.detail),
                    "ingredients": text[:400],
                }
            )
        for check in seen:
            labels_with[check] += 1

    elapsed = time.time() - started
    summary = {
        "export": args.export.name,
        "export_sha256": digest,
        "records_in_export": total,
        "selection_rule": f"ingredients_text of at least {MIN_INGREDIENTS_CHARS} characters",
        "labels_selected": kept,
        "labels_that_parsed": parsed,
        "crashes": crashes,
        "ingredients_parsed": ingredient_count,
        "findings_by_check": dict(per_check),
        "labels_with_at_least_one_finding_by_check": dict(labels_with),
        "seconds": round(elapsed, 1),
        "register": {
            annex: {"last_update": v[0], "sha256": v[1], "entries": v[2]}
            for annex, v in register.info.annexes.items()
        },
    }
    print(json.dumps(summary, indent=2))

    if args.samples:
        rng = random.Random(args.seed)
        drawn = {
            check: rng.sample(rows, min(args.sample_size, len(rows)))
            for check, rows in samples.items()
        }
        args.samples.write_text(
            json.dumps({"summary": summary, "samples": drawn}, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
