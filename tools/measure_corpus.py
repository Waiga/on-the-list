#!/usr/bin/env python3
"""Run on-the-list over an Open Beauty Facts export and report what happened.

This script produces automated corpus counts and seeded sample selection. Human
review, not this script, produces the audit judgments.

    curl -sO https://static.openbeautyfacts.org/data/en.openbeautyfacts.org.products.csv.gz
    shasum -a 256 en.openbeautyfacts.org.products.csv.gz
    python3 tools/measure_corpus.py en.openbeautyfacts.org.products.csv.gz

The export is Open Database Licence 1.0, which is share-alike and therefore
incompatible with redistributing a filtered subset inside an MIT repository. It
is not vendored here. Only the measurements are published, and the hash above
is how you check you have the same file. The pinned export SHA256 is
``d527f033d2549b86424db0ef1e87b785f92f53901036afd0c0a24bd629a766a5``.
Reproducing the published automated counts and seeded selections also requires
measurement code revision
``f72f866974a8f5a4af27a22ac33d0fbae94c5227``.

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
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from on_the_list.analyse import analyse  # noqa: E402
from on_the_list.ingredients import component_headings, looks_like_prose  # noqa: E402
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
    # The defaults select the seeded samples described in the corpus manifest.
    # The script redraws those rows but does not reproduce human judgments.
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    digest = hashlib.sha256(args.export.read_bytes()).hexdigest()
    register = load()

    csv.field_size_limit(10**8)
    total = kept = crashes = 0
    parsed = 0
    ingredient_count = 0
    per_check = Counter()
    labels_with = Counter()
    # Automated corpus counts published in the README and manifest. Human audit
    # judgments are recorded separately and are not produced here.
    prohibited_by_condition = Counter()
    labels_by_condition = Counter()
    prohibited_by_entry = Counter()
    considered_by_entry = Counter()
    warning_by_statement = Counter()
    colourant_by_name = Counter()
    non_colourants_after = Counter()
    repeated_shape = Counter()
    prose_labels = 0
    multi_section_labels = 0
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
        if any(looks_like_prose(item) for item in report.ingredients):
            prose_labels += 1
        if component_headings(text):
            multi_section_labels += 1
        for exclusion in report.considered:
            considered_by_entry[exclusion.entry.citation] += 1
        conditions = set()
        seen = set()
        for finding in report.findings:
            per_check[finding.check] += 1
            seen.add(finding.check)
            if finding.check == "prohibited":
                key = "conditional" if finding.qualified else "unconditional"
                prohibited_by_condition[key] += 1
                conditions.add(key)
                if not finding.qualified:
                    prohibited_by_entry[finding.citation] += 1
            elif finding.check == "colourant-order":
                match = re.match(r"(\S+ ?\S*) is a colour index", finding.summary)
                colourant_by_name[match.group(1).lower() if match else "?"] += 1
                match = re.search(
                    r"before (?:(\d+) entries|one entry)", finding.summary
                )
                non_colourants_after[
                    int(match.group(1)) if match and match.group(1) else 1
                ] += 1
            elif finding.check == "repeated-entry":
                repeated_shape[
                    "whole list repeated"
                    if "printed more than once" in finding.summary
                    else "one name repeated"
                ] += 1
            elif finding.check == "warning-wording":
                match = re.search(r"the statement '([^']+)'", finding.summary)
                warning_by_statement[match.group(1) if match else "?"] += 1
            samples.setdefault(finding.check, []).append(
                {
                    "code": record.get("code"),
                    "summary": finding.summary,
                    "detail": list(finding.detail),
                    "ingredients": text[:400],
                }
            )
        for key in conditions:
            labels_by_condition[key] += 1
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
        "prohibited_findings_by_condition": dict(prohibited_by_condition),
        "labels_with_a_prohibited_finding_by_condition": dict(labels_by_condition),
        "unconditional_prohibited_findings_by_annex_entry": dict(
            prohibited_by_entry.most_common()
        ),
        "considered_and_not_counted": sum(considered_by_entry.values()),
        "considered_and_not_counted_by_annex_entry": dict(
            considered_by_entry.most_common()
        ),
        "warning_findings_by_statement": dict(warning_by_statement.most_common()),
        "colourant_findings_by_name": dict(colourant_by_name.most_common(15)),
        "non_colourants_following_a_colourant": dict(
            sorted(non_colourants_after.items())
        ),
        "repeated_findings_by_shape": dict(repeated_shape),
        "labels_with_pack_prose_in_the_panel": prose_labels,
        "labels_whose_field_carries_a_section_heading": multi_section_labels,
        "seconds": round(elapsed, 1),
        "register": {
            annex: {"last_update": v[0], "sha256": v[1], "entries": v[2]}
            for annex, v in register.info.annexes.items()
        },
    }
    print(json.dumps(summary, indent=2))

    if args.samples:
        # One row per label, not per finding. The seeded selections in
        # docs/corpus-manifest.md were drawn from a deduplicated list. Human
        # review is required to turn these selected rows into audit judgments.
        rng = random.Random(args.seed)
        drawn = {}
        for check, rows in samples.items():
            seen_codes: set[str] = set()
            unique = [
                row
                for row in rows
                if not (row["code"] in seen_codes or seen_codes.add(row["code"]))
            ]
            drawn[check] = rng.sample(
                unique, min(args.sample_size, len(unique))
            )
        args.samples.write_text(
            json.dumps({"summary": summary, "samples": drawn}, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
