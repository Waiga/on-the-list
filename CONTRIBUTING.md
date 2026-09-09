# Contributing

Contributions should improve evidence quality, reproducibility, failure safety,
or clarity. More checks and more output are not automatically improvements.

## Setup

```bash
python3 -m pip install --no-deps .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

No dependencies, and `pyproject.toml` says `dependencies = []`. A test asserts
that, because the offline guard only reads this package's source and that is
only good enough while there is nothing else in the install to read.

## Change standard

1. Start from a scoped issue, or explain the observed problem in the pull
   request.
2. Add a failing test for a behaviour change.
3. Make the smallest implementation that passes it.
4. Run the full suite.
5. Update the README, `docs/limitations.md` and `docs/corpus-manifest.md` when
   commands, evidence, limitations or output change.
6. Disclose material AI assistance and confirm that you reviewed the result.

## The rules this repository will not bend on

**No verdicts.** Nothing in the output may say that a product is compliant,
safe, legal, permitted, banned or clean. Every finding is a statement about two
strings: one printed on the input, one printed in a published annex. A test
checks the output for the words.

**Absence is not a defect.** Annexes II to VI list restricted substances. An
ingredient no entry names is *not restricted by these annexes* and nothing more.
There is no `unknown` category, and a change that introduces one will be closed.
The reasoning is in `docs/superpowers/specs/2026-09-09-on-the-list-design.md`.

**No check may depend on a concentration.** A label does not state one.

**The analysis path stays offline.** `fetch.py` is the only module allowed to
open a connection, nothing on the analysis path may import it at module level,
and `tests/test_offline.py` enforces both statically and at runtime. Adding an
import to the allowlist there is a deliberate act with a test to change, which
is the friction intended.

**A check that did not run is not a check that found nothing.** Every report
lists all four checks with a reason for any that did not run. Do not remove
that.

## Changing the register

The five CSVs in `on_the_list/data/` are the Commission's bytes, unmodified, and
their hashes are in `registry_manifest.py`. To update them:

```bash
on-the-list update-register --into on_the_list/data
on-the-list register          # read the new hashes and dates
```

Then update `registry_manifest.py` — filename, hash, size, dates, row count —
and re-run the suite. Several tests assert counts derived from the register
(1,913 distinct names, 314 named Annex II rows, 38 entries with an extractable
warning statement); if those move, the numbers in the README have moved too, and
both must be corrected in the same change. That coupling is deliberate.

Never hand-edit a CSV. The value of the vendored copy is that a stranger can
`curl` the API and get the same bytes.

## Measuring

Any claim about how well a check works has to come from
`tools/measure_corpus.py` over a corpus whose source, date and hash are recorded
in `docs/corpus-manifest.md`. A rate that improved because the tool was tuned
against the corpus it is measured on is not an improvement; say what changed and
why it is a correctness fix rather than a fit to one dataset.

If a check turns out to be useless, the change that establishes that should
either remove it or say plainly in the README that it is useless. Quietly
raising a threshold until the number looks better is the failure this section
exists to prevent.

## Where to start

`docs/limitations.md` lists what the tool cannot do. Several entries there are
gaps someone could close: names the Commission writes differently from a pack,
OCR forms not yet recognised, and the multi-component-pack problem behind the
repeated-entry check's error rate.

## Review expectations

Maintenance is best effort by a single maintainer working in a weekly review
block, so a response can take days. Small, tested, single-purpose changes are
reviewed fastest.

Never include credentials, private data, copied proprietary code, or unlicensed
assets. Reviewers may close changes that manufacture activity, inflate claims,
or expand scope without evidence.
