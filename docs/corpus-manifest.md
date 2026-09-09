# Manifest

Every number published about this tool was produced against the exact material
described here. The point of the hashes is that you can obtain the same files
and check, and that when one of them changes you can tell.

## The register: CosIng Annexes II to VI

**Source.** The European Commission's CosIng API. No key, no account, no rate
limit published.

```
https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/{ANNEX}/export-csv
```

for `ANNEX` in `II`, `III`, `IV`, `V`, `VI`. Each returns `200` with
`Content-Type: text/plain; charset=UTF-8`.

**Retrieved.** 9 September 2026. The Commission's own last-update stamp on all
five files is 28 August 2026.

**Selection rule.** All five files, whole, unmodified. Nothing is filtered,
reformatted or corrected on the way in. What is committed to
`on_the_list/data/` is the bytes the API served.

| Annex | Rows | Bytes | SHA-256 |
|---|---|---|---|
| II — prohibited substances | 1,758 | 650,518 | `b7105a05bf724bb10cebaac3a3813b6146c3153ae1d07097d35bb1f73cd7283b` |
| III — restricted substances | 381 | 296,566 | `82263556bab69a05b508b92e42dbeceec56f201a62ded2dd513198f6b029dd53` |
| IV — permitted colourants | 154 | 47,319 | `bed185d597cec2e119b05eb8fb43adc07d3ddc1aa6ed0a2ee64308f790b5b84b` |
| V — permitted preservatives | 58 | 31,439 | `e6db8b8b90d4082ec83bcc9d1fffcd8993b501d1e8116de057c772a347d10b12` |
| VI — permitted UV filters | 34 | 19,161 | `b672b81a2a090b56bf09bbd554764a6f0c8dd8104761a0e87933e555df775774` |

Check any of them:

```bash
curl -s https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/V/export-csv | shasum -a 256
# e6db8b8b90d4082ec83bcc9d1fffcd8993b501d1e8116de057c772a347d10b12
```

Or read what the installed package is actually using:

```bash
on-the-list register
```

**Derived counts.** 1,913 distinct names across the five annexes after folding,
of which 146 are colour index numbers. 314 of Annex II's 1,758 rows carry an
INCI name at all. 38 of the 627 entries in Annexes III to VI yield a
`Contains …` statement the warning check will look for, giving 35 distinct
statements. Every one of those is asserted by a test in `tests/test_register.py`
and `tests/test_annexes.py`, so a change to the parser that moves them fails the
suite rather than quietly restating the README.

**Licence.** European Commission material. Reuse is governed by Commission
Decision 2011/833/EU of 12 December 2011; the Commission's legal notice states
that content it owns on its websites is licensed under CC BY 4.0. Attribution,
carried in `registry_manifest.py` and printed by `on-the-list register`:

> CosIng, © European Union, 1995-2026. Annexes II to VI of Regulation (EC)
> No 1223/2009, retrieved from the European Commission CosIng API. Reused under
> Commission Decision 2011/833/EU (CC BY 4.0). Unmodified.

## The corpus: Open Beauty Facts

**Source.**

```
https://static.openbeautyfacts.org/data/en.openbeautyfacts.org.products.csv.gz
```

**Retrieved.** 9 September 2026. The server reported
`Last-Modified: Wed, 09 Sep 2026 00:22:35 GMT`.

**SHA-256.** `d527f033d2549b86424db0ef1e87b785f92f53901036afd0c0a24bd629a766a5`
(17,884,435 bytes, gzipped).

**Records in the export.** 64,237.

**Selection rule.** Every record whose `ingredients_text` field is at least 50
characters. Nothing else is filtered, sorted or sampled. That gives **16,635
labels**.

The 50-character floor is a real limit on what the measurement proves. A parse
rate of 16,593 out of 16,635 is partly guaranteed by that selection and is not
an achievement of the parser.

**Reproduce it.**

```bash
curl -sO https://static.openbeautyfacts.org/data/en.openbeautyfacts.org.products.csv.gz
shasum -a 256 en.openbeautyfacts.org.products.csv.gz
python3 tools/measure_corpus.py en.openbeautyfacts.org.products.csv.gz
```

`tools/measure_corpus.py` prints the whole summary as JSON, including the
register hashes it ran against, so a result carries its own provenance. Add
`--samples out.json` to draw a reproducible sample of findings for auditing; the
seed is fixed and printed in the script.

Open Beauty Facts is republished daily. The hash above is how you can tell
whether you have the file these numbers came from. If you do not, expect the
counts to move.

**Licence.** Open Database Licence 1.0. ODbL is share-alike, which is
incompatible with redistributing a filtered subset inside an MIT repository, so
**the corpus is not vendored here**. Only the measurements are published.

**What the corpus cannot measure.** It carries no field holding the text printed
on a pack — `packaging_text` describes materials, not warnings — so the
warning-wording check's accuracy is untested. See `docs/limitations.md`.

## The hand audits

Three samples were read by hand against the underlying documents. Each is
reproducible from the corpus above.

| Check | Sample | Method | Wrong |
|---|---|---|---|
| prohibited | all 20 Annex II entries behind the 1,074 unconditional findings | each entry's chemical name read against the annex text | 1 entry, 101 findings (9.4%) |
| colourant-order | 30 findings, `random.Random(11)` over the deduplicated finding list | each read against the label's own printed list | 3 (10%) |
| repeated-entry | 30 findings, same draw | same | 15 (50%) |

The prohibited audit is exhaustive over entries rather than sampled over
findings, because 20 entries account for all 1,074 unconditional findings and
reading 20 annex rows settles every one of them.
