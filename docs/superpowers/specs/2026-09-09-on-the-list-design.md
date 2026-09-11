# on-the-list — design

9 September 2026.

> **Correction, 11 September 2026.** The original design overstated the
> repeated entry evaluation by treating an incompletely recorded sample result
> as a corpus rate. A fresh row level audit of the same seeded sample found 21
> false positives and 9 findings that correctly described a repeated normalized
> name in the historical recorded text. This is a result for 30 sampled
> findings, not a population rate. Not every sound row had a usable package
> image, and two sound rows are different barcodes with the same recorded
> formula. The public [row level audit](../../audits/repeated-entry-audit.md)
> records every judgment and evidence basis.

## What it is

A command-line tool that reads a cosmetic ingredient list and reports what
Annexes II to VI of Regulation (EC) No 1223/2009 say about the ingredients on
it, as the European Commission publishes them. It runs on the user's machine,
against a register shipped inside the package, and it issues no verdict.

## The constraint everything else follows from

Both halves of every comparison must be present: one printed on the input, one
printed in a shipped authoritative reference. Nothing is inferred, nothing is
looked up remotely at analysis time, and the absence of evidence is reported as
absence of evidence.

That rules out, before any code was written:

- any check that needs a concentration, because a label does not state one;
- any check that needs to know the product type, because a label does not state
  that either;
- any statement that a product is compliant, safe, legal or clean;
- any "did you mean" or fuzzy matching, because a near-match against a
  prohibited-substances list is a confident claim about a substance the label
  does not contain.

## The check that was ruled out, and why it matters most

**"Is that a real INCI name?" is not a check this tool can make.**

It was the obvious first idea. A tool holding 1,913 names read out of an
official register, and a printed list, looks exactly like a spell-checker for
INCI names, and that is what a reader will assume it is. (They are names as the
register prints them, from two columns, one of which also holds chemical and
CAS-style identifiers. It is not a list of 1,913 INCI names.)

It is wrong, and the reason is a property of the source rather than a limitation
of the implementation. **Annexes II to VI are lists of restricted substances.**
Annex II is what may not be used, III what may be used under restrictions, and
IV, V and VI the permitted colourants, preservatives and UV filters. There is no
annex that lists what is *allowed in general*, because in the EU an ingredient
is allowed unless something restricts it.

The finding that settled it: **no entry in any of the five annexes is named Aqua
or Glycerin.** The two most common ingredients in cosmetics. They are absent
because nothing restricts them. Both words do occur elsewhere in the text --
"Glycerin" among the permitted coatings in the Annex VI titanium-dioxide entry,
"Nitroglycerin" as Annex II entry 253 -- but neither is an entry naming the
ingredient, which is what a lookup asks.

A validity check built on these annexes would therefore flag almost every
ingredient of almost every product. Softening it — flagging only "unusual"
absences — would be worse, because it would be a guess dressed as a check.

There is no public alternative source. The INCI dictionary is published by the
Personal Care Products Council and is proprietary; there is no redistributable
machine-readable list of valid INCI names.

So the tool has no notion of an invalid name. Absence from the annexes is
reported as **not restricted by these annexes** and means only that. The word
`unknown` does not appear in the output, the models module has no field for it,
and a test asserts that Aqua, Water, Glycerin and Parfum match nothing and
produce no finding.

This is stated first in the README because it is the most likely way to misread
the tool, and a reader who misreads it will take a clean report as a validation
it never performed.

## The reference data

The Commission's CosIng API serves each annex as CSV with no key:
`https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/{ANNEX}/export-csv`.
About 1.05 MB for all five.

**Vendored rather than fetched.** The five files are committed to
`on_the_list/data/` as the API served them, byte for byte, with their SHA-256 in
`registry_manifest.py`. This is allowed: European Commission material is
reusable under Commission Decision 2011/833/EU, and the Commission's legal
notice states that content it owns is licensed under CC BY 4.0. The attribution
is carried in the manifest and printed by `on-the-list register`.

Vendoring the raw bytes rather than a derived extract was deliberate. A derived
file would be smaller and tidier, but a stranger could not verify it against the
source with one `curl` and one `shasum`. Verifiability beat tidiness.

The register is dated by the Commission's own last-update stamp, hashed, and
named in every report. A result therefore cites the version of the law it was
produced against, and when the Commission republishes, the hash stops matching
and the staleness is visible instead of silent.

### What reading the CSVs actually required

None of this was in the plan; all of it came from the files.

**Row 4 is the header.** Rows 0 to 3 are a file creation date, the annex number
and its last-update date, the annex title, and a spanning group header.

**Two columns hold names, with different separators.**
`Name of Common Ingredients Glossary` (and its Annex IV variant
`Colour index Number / Name of Common Ingredients Glossary`) separates names
with `;` and `/`, never a comma. `Identified INGREDIENTS or substances e.g.`
separates with commas — but chemical names contain commas of their own:
`N,N-DIETHYL-m-AMINOPHENOL`, `1,3-Bis(hydroxymethyl)-3-thiourea`,
`PEG-3,2',2'-Di-p-PHENYLENEDIAMINE`. A plain `split(",")` gives a different
answer from the parser on 52 rows and leaves a one-character fragment on 38 of
them, putting a substance called `N` into the register.

The rule adopted: a comma is part of a name when the fragment before it ends in
a locant — a digit, a prime, or a lone letter — **and** the fragment after it
begins like a locant continuation. Both halves are needed. `CI 77480,GOLD` ends
in a digit and is a real separator; `DICHLOROMETHANE,4,6-DIMETHYL-PYRAN-2-ONE`
starts with a digit and is also a real separator. It is a heuristic over an
undocumented column, so it is written down as one; its failure mode is a
fragment that matches nothing, which is a missed match rather than a false one.

**`csv.reader` must be given a file object, not a list of lines.** A quoted
field may contain newlines and the annexes use them heavily — a wording cell is
often ten lines. Feeding `csv.reader` the output of `splitlines()` glues those
lines together with nothing between them. It reported no error, and it turned
`Contains selenium disulphide\nAvoid contact with eyes` into one run-on string,
leaving 32 of the 38 extractable warning statements, 19 of them running on into
the sentence after them. Every test was green.

**Names carry typesetting artefacts** from the PDF the annexes are laid out
from: `ANTHRA- 9,10-QUINONE`, `MEA- SALICYLATE`, `1-ACETOXY-2-METHYLNAPH-THALENE`.
Folding removes spaces around hyphens, which repairs the first two. The third is
a hyphenation break that cannot be undone without corrupting real names, and is
left.

**The maximum-concentration column is unusable and unused**, per the constraint
above.

## The checks

Each is switchable with `--skip`, and every report lists all four with whether
they ran and, if not, why. A check that did not run must never read as a check
that found nothing.

### 1. prohibited

An ingredient's folded name equals a name on an Annex II entry. Reported with
the entry number and the entry's own chemical name, so a reader can open the
annex.

Four narrowings, each because the alternative was measured and was wrong:

- **Conditional entries go in their own group.** Many Annex II entries carry a
  condition in the Commission's own wording. A lexical scan for *except*,
  *unless*, *when used*, *other than*, *with the exception of*, *only if*,
  *only when*, *provided that* and a bare *if* separates them. The bare *if* is
  included because all 333 Annex II entries containing one state a condition on
  composition that a name cannot settle: 149 read "if it contains > 0,1 % w/w
  Butadiene" and the rest name another impurity, such as entry 613's "Pitch,
  coal tar-petroleum, if it contains > 0.005 % w/w benzo[a]pyrene". The tool
  never decides whether a condition is met; it prints the wording.
- **A nano-only entry whose own INCI names do not say nano is not reported.**
  Annex II entry 1725 is `Styrene/Acrylates copolymer (nano)` beside the
  ordinary INCI name. 421 corpus labels printing the ordinary polymer matched
  it. They go to *considered and not counted*.
- **A match on a fragment of a printed name is not reported.**
  `CI 77288 / CHROMIUM` matched the entry for chromium metal. Over 16,635 labels
  fragment matches produced no correct finding. A name with a bracketed aside
  removed still counts as the whole name.
- **A prohibition qualified by another annex says which.** Hydroquinone is
  prohibited "with the exception of entry 14 in Annex III". Printing only the
  prohibition is a half-truth.

### 2. colourant-order

A `CI NNNNN` colourant printed before a non-colourant, in the declared section
only. Article 19(1)(g) allows colourants in any order after the other
ingredients.

Restricted to bare colour index forms — plus the `CI NNNNN:N` lake suffix and
the `Cl NNNNN` that scanners produce — because named Annex IV substances mostly
do more than one job. Titanium Dioxide is an Annex IV colourant, an Annex VI UV
filter and an opacifier; its position says nothing about which.

The derogation is permissive, not mandatory, so a colourant in weight order is
not necessarily misplaced. The finding says where a name is printed and prints
the hair-dye and sub-1% caveats with it. A seeded review judged 4 of 30 findings
wrong. That sample result is not a population rate.

### 3. repeated-entry

The same folded name twice in the declared section. No register involved. When
most of the list repeats, it is reported once as the same panel printed more
than once rather than as thirty findings.

### 4. warning-wording

Only with `--pack-text`. An Annex III–VI entry attaches a `Contains …` statement
to a matched ingredient and that statement is not in the supplied text.

The narrowness is the whole reason it is worth running. The wording column mixes
label text with purity criteria and manufacturing conditions that are nothing to
do with a label. Only `Contains …` statements are extracted: 38 entries, 35
statements. Everything else is shown to the reader, labelled as attached but not
searched for.

An earlier version also extracted quoted passages, since the annexes quote the
long hair-dye warnings. Abandoned: the annexes use apostrophes as quotation
marks and the quoted text contains apostrophes, so the extractor produced
fragments like `tattoo in the past`. A rule that yields garbage on the inputs it
was written for is not a rule.

Reported as a **gap between two documents**, never a violation, and printed with
the entry's full wording so a reader can see when the requirement is itself
conditional ("Above 2%: Contains ammonia").

### Coverage

How many ingredients no entry names, labelled *not restricted by these annexes*.
Never a finding, never an error.

## Offline boundary

`fetch.py` is the only module that can open a connection, and nothing on the
analysis path imports it. The command line reaches it from inside the
`update-register` function only.

`tests/test_offline.py` enforces this four ways: an AST allowlist over every
module except `fetch.py`, following `follow-through`'s pattern; a check that no
module imports `fetch` at module level; a real analysis run with `socket.socket`
replaced by something that raises; and a check that the package contains nothing
but Python source and the five declared CSVs, each still matching its hash.

Every detector has a test proving it can fail.

## What the measurement changed

The corpus run over 16,635 real labels was not a validation exercise; it
rewrote the tool. Every item below was a defect that produced a wrong finding
rather than an error, and none was visible from the unit tests:

- `csv.reader` over `splitlines()` destroying newlines in quoted fields;
- comma-splitting the identified-ingredients column;
- the nano-only Annex II entry, 421 findings;
- HTML entities resolved after splitting rather than before, so `&lt;` became an
  ingredient called `&lt`;
- `[+/- CI 77491, CI 77492]` not recognised, so a shade-range block was read as
  declared ingredients;
- toothpastes printing `Contient du fluorure de sodium (1450 ppm)` straight on
  from the list;
- `Cl 77492` with a lowercase L;
- `Styrene / Acrylates Copolymer` split as two synonyms, matching the styrene
  monomer in Annex II on 35 labels;
- a bracket holding most of a name -- `Styrene (Acrylate Copolymer)` -- treated
  as an aside, so what was left matched Annex II while the same substance
  printed the other way round, `CI 77288 / CHROMIUM`, did not;
- a leading "Ingredients:" left on the first ingredient of a file handed to
  `--ingredients`, which is how such files usually start;
- a printed tolerance, `Glycerin +/- 0.5%`, opening a shade-range block;
- a quadratic position check: 20,000 colour index numbers took 64 seconds;
- a colourant found only in Annex II described as "listed in Annex IV";
- a malformed `--register` directory raising a traceback and exiting 1;
- `--skip` on every check exiting 0;
- the Annex III to VI matches never being printed at all, which is the tool's
  own title.
- fragment matches against Annex II;
- a quarter of the corpus having pack prose inside the panel, now reported;
- a tenth of it holding more than one product's list, now detected where a
  heading exists and used to suppress both order-dependent checks.

Two limitations remain published rather than patched. The Cyclomethicone/D4
mapping was responsible for 99 of 1,066 unconditional findings in the pinned
corpus group. The repeated entry audit found 21 false positives and 9 sound
findings in a seeded sample of 30. The sample result is not a population rate.

## What was considered and rejected

**A derived, reduced register file.** Smaller and faster, but not verifiable
against the source in one command.

**Fuzzy or substring matching.** Would find misspellings; would also produce
confident false claims against a prohibited-substances list. Not worth it.

**An exception list for Cyclomethicone and the other known false positives.**
This would be tuning the tool against the single corpus it was measured on, and
it would make the published corpus result a description of the tuning rather
than of the tool.

**Removing the repeated-entry check.** The fresh audit found both false
positives and sound findings in the seeded sample. False positives came from
multi product or multi component fields, OCR, transcription, or parser
artifacts, and fields that were not one cosmetic ingredient declaration.
Removing the check would lose supported literal repeated name findings.
Keeping it without the bounded sample result and its causes would be dishonest,
so both are published.

**Language-specific heuristics for splitting multi-component packs.** Several
were tried. Each either caught almost nothing more or suppressed real findings.
None is in the tool.
