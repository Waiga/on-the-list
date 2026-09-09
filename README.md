# on-the-list

Reads a cosmetic ingredient list and reports what the EU's official annexes say
about the ingredients on it.

Runs entirely on your machine. No account, no API key, no upload, no
dependencies beyond Python itself. The annexes are shipped with the package;
downloading a fresh copy is a separate command you have to type.

```
$ on-the-list examples/shade-stick.txt

on-the-list 0.1.0 — examples/shade-stick.txt
CosIng annexes II-VI, Commission last update 28/08/2026, 1913 distinct names,
read from the copy shipped with this package

10 ingredients read. 2 prohibited, 1 colourant order, 1 repeated entry.

NAMES THAT MATCH AN ANNEX II ENTRY
  Annex II is the list of substances prohibited in cosmetic products. A match
  is reported here as a match. Whether it means anything about this product
  is for someone with the formulation in front of them.

  Butylphenyl Methylpropional matches Annex II, entry 1666, in the
  Commission's list of substances prohibited in cosmetic products.
      printed as: Butylphenyl Methylpropional
      register name: BUTYLPHENYL METHYLPROPIONAL (read from the 'identified'
      column)
      annex entry: 2-(4-tert-butylbenzyl) propionaldehyde
```

## The thing to understand before anything else

**An ingredient that appears in none of the annexes is not an error, and this
tool never reports it as one.**

Annexes II to VI are lists of *restricted* substances: prohibited, restricted,
permitted colourants, permitted preservatives, permitted UV filters. They are
not an inventory of valid INCI names. Aqua and Glycerin appear in none of them,
because nothing restricts Aqua or Glycerin.

So *"that is not a real INCI name"* is not a check this tool can make, and it
does not attempt one. Absence from the annexes means **these annexes say
nothing about it**, and the report says exactly that, in those words. There is
no `unknown` and no `unrecognised` anywhere in the output.

This is the most likely way to misread the tool, which is why it is the first
thing on the page. The reasoning is set out in full in
[`docs/superpowers/specs/2026-09-09-on-the-list-design.md`](docs/superpowers/specs/2026-09-09-on-the-list-design.md).

## What it does not do

It never says a product is compliant, safe, legal, permitted or clean. It
compares names printed on a label with names printed in a published annex, and
reports where they coincide. Whether that means anything about a particular
product depends on its concentration, its product type, its route of exposure
and its formulation, none of which an ingredient list states.

That is not modesty. It is the only claim the evidence supports.

## Install

```bash
pip install .
```

Python 3.11 or newer. Nothing else.

## Use

```bash
on-the-list label.txt                      # whole pack text; the list is found in it
cat product-page.txt | on-the-list -
on-the-list --ingredients inci.txt         # you already have just the list
on-the-list --ingredients inci.txt --pack-text pack.txt   # runs the warning check too
on-the-list label.txt --format markdown    # to paste into an email
on-the-list label.txt --format json        # for a pipeline
on-the-list label.txt --skip colourant-order
on-the-list --list-checks
on-the-list register                       # which register is in use, and its hashes
on-the-list update-register                # the only command that uses the network
```

Exit codes: `0` nothing found, `1` at least one finding, `2` could not run. A
label whose ingredient list did not parse exits `2`, never `0`, and so does a
run with every check switched off: a green CI job over a label that nothing was
compared to is the one thing this tool exists not to do.

## The four checks

Each one can be switched off on its own with `--skip`, and the report always
prints which ran and which did not, with a reason. A check that did not run must
never read as a check that found nothing.

| | |
|---|---|
| **prohibited** | An ingredient's name matches an entry in **Annex II**. Reported as a match with the entry number, split into entries that say something unconditional about the substance and entries whose own wording sets a condition. |
| **colourant-order** | A `CI NNNNN` colourant is printed before a non-colourant. Article 19(1)(g) allows colourants in any order *after* the other ingredients, so this is a positional observation with no judgement in it. |
| **repeated-entry** | The same name appears twice in the declared list. Needs no register at all. |
| **warning-wording** | An annex attaches a `Contains …` statement to an ingredient on the list, and that statement is not in the pack text you supplied. Reported as a **gap between two documents**, never as a violation: the wording may be printed somewhere the supplied text does not cover, in another language, or the entry's condition may not apply. It needs pack text to search — a whole label file counts as that, `--ingredients` on its own does not — and it says which when it does not run. |

Two things that are not checks and change no exit code:

**What the annexes name.** Every entry in Annexes II to VI that names an
ingredient on the list, with what that annex is — prohibited, restricted, a
permitted colourant, preservative or UV filter — and the product types the entry
is limited to. This is the tool's own title, and for a while it was the one
thing the report did not print: a label containing Phenoxyethanol produced no
finding, and the reader was told one of three ingredients was named somewhere
and never told where.

**Coverage.** How many ingredients no annex entry names, labelled *not
restricted by these annexes*.

### Four narrowings that cost coverage on purpose

**The position check uses only bare `CI NNNNN` forms.** Named Annex IV
substances are not used, because most do more than one job: Titanium Dioxide is
an Annex IV colourant, an Annex VI UV filter and an opacifier, and where it
sits in a list proves nothing about which of those it is doing. A CI number is
unambiguous.

**Only `Contains …` statements are searched for in pack text.** The annexes'
wording column mixes label text with conditions that have nothing to do with a
label — *"Purity criteria as set out in Commission Directive 95/45/EC (E 129)"*,
*"Only nanomaterials having the following characteristics are allowed"*.
Treating the whole column as label text would report a missing warning on every
sunscreen containing zinc oxide. 38 of the 627 entries in Annexes III to VI
yield a statement this tool will look for; the rest are shown to the reader and
not searched for, and the report says so.

**A match on part of a printed name is not reported against Annex II.**
`CI 77288 / CHROMIUM` is a colourant printed beside its element name, and the
fragment `CHROMIUM` matches the Annex II entry for chromium metal. Over 16,635
real labels, fragment matches produced no correct Annex II finding at all, so
they are shown under *considered and not counted* with the reason instead. A
name with a bracketed aside removed — `Titanium Dioxide (nano)` → `Titanium
Dioxide` — is still the name of the ingredient, and does match.

**Nothing is built on a concentration.** A label does not state one. Every
maximum-concentration column in the annexes is unused.

## Reproducibility

The register shipped in this package is the European Commission's own CosIng
export, byte for byte. Every report names the version it used, and you can
check it:

```bash
$ on-the-list register
CosIng annexes II-VI, Commission last update 28/08/2026, 1913 distinct names,
read from the copy shipped with this package

CosIng, © European Union, 1995-2026. Annexes II to VI of Regulation (EC)
No 1223/2009, retrieved from the European Commission CosIng API. Reused under
Commission Decision 2011/833/EU (CC BY 4.0). Unmodified.

Annex II — list of substances prohibited in cosmetic products
  1758 entries, Commission last update 28/08/2026
  sha256 b7105a05bf724bb10cebaac3a3813b6146c3153ae1d07097d35bb1f73cd7283b
  https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/II/export-csv
```

```bash
curl -s https://api.tech.ec.europa.eu/cosing20/1.0/api/annexes/II/export-csv | shasum -a 256
```

If that hash no longer matches, the Commission has republished the annex, and a
result produced against the old one is a result about a document that no longer
exists. `on-the-list update-register` downloads the current files; the report
then names the new hashes instead.

Full manifest, including the corpus used for the measurements below:
[`docs/corpus-manifest.md`](docs/corpus-manifest.md).

## Measured against real labels

Unit tests pass on the inputs their author imagined, which proves very little.
This was run over **16,635 real published cosmetic labels** from an Open Beauty
Facts export — real packs, real messiness, none of it written by this project.
The selection rule is every record in the export whose `ingredients_text` field
is at least 50 characters. Nothing else is filtered or sampled.

`tools/measure_corpus.py` is the script that produced every number here.

| | |
|---|---|
| Records in the export | 64,237 |
| Labels selected | 16,635 |
| Labels whose list parsed | 16,535 |
| Crashes | 0 |
| Ingredients parsed | 298,423 |
| **Annex II matches** | **2,408** on 2,037 labels |
| — where the annex entry is unconditional | 1,066 on 942 labels |
| — where the annex entry sets a condition | 1,342 on 1,167 labels |
| Colourant position | 975 on 645 labels |
| Repeated entries | 712 on 291 labels |
| Warning wording not found | 1,170 on 1,027 labels |
| Considered and not counted | 554 |
| Labels with pack prose inside the ingredient panel | 4,288 (25.8%) |
| Labels whose ingredient field carries a section heading | 1,631 (9.8%) |

Every one of those comes out of `tools/measure_corpus.py`, including the
per-entry and per-statement breakdowns quoted below. `--samples` draws the
audit samples with the seed and size the manifest names.

### How wrong each check is

Hand-audited against the published annex text or the label's own list. These
are the numbers, not a summary of them.

**prohibited — 9.3% wrong on the unconditional group.** All 19 Annex II entries
behind the 1,066 unconditional findings were read against the annex text.
Eighteen are correct: Butylphenyl Methylpropional (651 findings), Zinc
Pyrithione (105), Hydroxyisohexyl 3-Cyclohexene Carboxaldehyde (100),
Pentasodium Pentetate (65), Ergocalciferol and Cholecalciferol (11), borates
(7), 4-Methylbenzylidene Camphor (5), Formaldehyde (4), and a tail of one to
three each. One is wrong, and it is the tool's largest single known false
positive: **Annex II entry 1388 is `Octamethylcyclotetrasiloxane; D4`, and the
Commission's own identified-ingredients column gives its INCI name as
`CYCLOMETHICONE`**. Cyclomethicone names a *mixture* of cyclic siloxanes, so a
label printing it has not said it contains D4. That produced 99 findings. There
is no mechanical signal separating this from a correct match, so it is reported
here rather than patched around.

The 1,342 conditional findings are counted neither right nor wrong, because an
ingredient list cannot settle them. They are dominated by entries whose
condition no label states: petrolatum *"except if the full refining history is
known"*, the furocoumarin entry that names ordinary citrus oils *"except for
normal content in natural essences used"*, and the colourants prohibited only
*"when used as a substance in hair dye products"*. Each is printed with its own
wording so a reader can see the condition and decide.

**colourant-order — 4 of 30 wrong.** Thirty findings drawn by
`tools/measure_corpus.py --samples out.json` (seed 11, one row per label), each
read against the label's own list. Two failures are pack prose that the parser
kept — Spanish marketing copy after the colourants, and an OCR'd panel where
the list has no commas at all. One is a make-up palette declaring several
shades in one field. One is an OCR'd label whose text before `INGREDIENTS` is
unreadable.

The underlying weakness is deeper than that rate suggests, and it is stated in
[`docs/limitations.md`](docs/limitations.md): the Regulation *permits*
colourants after the other ingredients but does not *require* it, so a colourant
in weight order is not necessarily out of place. The check reports where a name
is printed and nothing more.

**repeated-entry — 16 of 30 wrong.** Thirty findings from the same draw, read
the same way. This is the weakest check in the tool and the number is not a
typo.

Eight of the sixteen are **multi-component packs**: a hair colour kit declaring
the crème, the developer and the conditioner in one field; a 2-in-1 shampoo. An
ingredient appearing once in each component is not a repeated ingredient. The
other eight are fields that are not one product's ingredient list at all — an
alphabetical glossary of every ingredient a brand uses, a food supplement, a
certification mark parsed as an ingredient, and OCR damage that split one name
into two.

The tool detects the multi-component case when the pack prints a heading it can
see — `Gel N°1:`, `MASQUE:`, a second `Ingredients:` — and then says so and does
not run either order-dependent check. It flagged 1,631 of the 16,635 labels that
way. It cannot detect it when the pack prints no heading, which is most of the
time, and no heuristic tried here improved that materially without losing real
findings.

**On a single product's own ingredient list — which is what the tool is for —
none of the sixteen failure modes applies.** All twelve sound findings in the
same sample were single-product lists. The corpus number is still the honest one
to publish, and it is 53%.

**warning-wording — not measured.** Open Beauty Facts carries no field holding
the text printed on a pack, so every finding in the corpus run is a gap by
construction and the rate means nothing. What the run does establish is that the
check fires on the right population: of the 1,170 findings, 692 are
`Contains sodium fluoride` on fluoride toothpastes, 132
`Contains sodium monofluorophosphate`, 127 `Contains hydrogen peroxide` on
developers, 93 `Contains ammonia` on hair colour and 48
`Contains Benzophenone-3` on sunscreens. Its accuracy is untested, and this
README will say so until a corpus with real pack text exists.

### What the measurement found that the tests did not

Every one of these was a real defect, found only by meeting 16,635 real labels
or by reading the annexes against their own text:

- **Feeding `csv.reader` a list of lines destroys newlines inside quoted
  fields.** The annexes put ten-line warning blocks in one cell.
  `Contains selenium disulphide\nAvoid contact with eyes` silently became one
  string. The extractor found 32 statements instead of 38, and 19 of the ones it
  did find ran on into the sentence after them. No error, all tests green. The
  reader uses `io.StringIO`.
- **The identified-ingredients column is comma-separated and its values contain
  commas.** A plain `split(",")` gives a different answer from the parser on 52
  rows, and on 38 of them it leaves a one-character fragment: a substance called
  `N`, from `N,N-DIETHYL-m-AMINOPHENOL`.
- **Annex II entry 1725 is `Styrene/Acrylates copolymer (nano)` and lists the
  ordinary INCI name beside it.** 421 labels printing the ordinary polymer
  matched a prohibited entry that is not about it. They are now reported as
  considered and not counted, with the reason.
- **HTML entities were resolved after splitting, not before.** The `;` inside
  `&lt;` is a separator: one Russian pack produced three ingredients called
  `&lt`, an American one produced three called `FD`, and each set was reported
  as a repeated ingredient.
- **`[+/- CI 77491, CI 77492]` closes its bracket after the colourants, not
  after the marker.** A pattern that expected `[+/-]` as a unit matched none of
  it, so a whole shade-range block was read as declared ingredients.
- **Toothpastes print `Contient du fluorure de sodium (1450 ppm de fluor)`
  immediately after the colourants with no break.** Read as an ingredient, it
  was the commonest reason a colourant appeared to be printed in front of a
  non-colourant.
- **`Cl 77492` with a lowercase L is endemic in scanned panels**, and appears
  beside a correctly read `CI` in the same list.
- **`Styrene / Acrylates Copolymer` is one name, not two.** Treating a spaced
  slash as a synonym separator left the fragment `Styrene`, which matches the
  styrene monomer in Annex II, on 35 real labels. Requiring a space on both
  sides of the slash left 21 of them; a polymer names its monomers with slashes,
  and the rule now says so, which leaves none.
- **Hydroquinone is prohibited by Annex II "with the exception of entry 14 in
  Annex III"**, where it is allowed in professional nail products. Reporting
  only the prohibition is a half-truth, so a match that also appears in another
  annex now says which.
- **Only 314 of Annex II's 1,758 rows carry an INCI name at all.** The rest are
  chemical or CAS identifiers with no cosmetic-glossary equivalent. The
  prohibited check can only see 18% of the prohibited list.
- **A file handed to `--ingredients` usually starts with the word
  "Ingredients:".** It was not stripped on that path, so the first ingredient
  became `Ingredients: Formaldehyde`, matched nothing, and the run exited 0 —
  while the same text through the whole-label path reported the match.
- **`Chromium (CI 77288)` was reported as prohibited and `CI 77288 / CHROMIUM`
  was not.** Same substance, two print orders, opposite answers. What survives a
  bracket being removed is the name only if it is at least half the words.
- **`Glycerin +/- 0.5%` opened a shade-range block.** Every declared ingredient
  after a printed tolerance dropped out of both order-dependent checks, and the
  report said only that the list had a "may contain" block.
- **The position check was quadratic.** 20,000 colour index numbers took 64
  seconds; the hostile-input tests never called the checks, only the parser.
- **A colourant found only in Annex II was described as "listed in Annex IV".**
  Four are: CI 12150, CI 20170, CI 27290 and CI 45425, each prohibited in hair
  dye. The finding now names the entries the register actually holds.
- **A malformed `--register` directory raised a traceback and exited 1** — the
  code for "findings were reported" — and the message about the Commission
  having changed the export format was unreachable.
- **`--skip` on all four checks exited 0.** Nothing was compared, and the report
  said "nothing found".

The corpus itself is not redistributed here. Open Beauty Facts is ODbL 1.0,
which is share-alike and incompatible with this repository's MIT licence. Only
the measurements are published, with the export's hash so you can obtain the
same file.

## What it misses

Stated plainly, because a checking tool that hides its blind spots is worse than
none. The long version is in [`docs/limitations.md`](docs/limitations.md).

- **It sees 18% of Annex II.** Most rows have no INCI name, so most prohibited
  substances cannot be matched against a label at all.
- **It cannot see concentration.** Most annex restrictions are limits, and a
  limit is not something a name can breach.
- **It cannot see product type.** A restriction on hair dye says nothing about a
  face cream, and an ingredient list does not say which the product is.
- **It matches exact names only, after folding.** No fuzzy matching, no
  substring search, no edit distance. A misspelling, a supplier's trade name, or
  a name the Commission writes differently will not match, and the tool will not
  tell you it missed one. It does look a printed name up under a bracketed or
  slash-separated part of itself — that is how `CI 77891` is found inside
  `Titanium Dioxide (CI 77891)` — but **only the Annex II check refuses a match
  found that way**; the other checks and the coverage count accept it.
- **It reads five annexes.** Annex I (the safety report) and Annex VII are not
  read, and neither is any national requirement, retailer standard, or rule
  outside the EU.
- **A pack panel inside the ingredient field derails everything.** A quarter of
  the corpus had prose in the panel. The tool says so when it can tell.
- **A "may contain" block is excluded from the position check** and is printed
  across a whole shade range, so nothing positional can be said about it.
- **Crowd-sourced label data can be wrong.** In the measurement above, a finding
  may be about a mistyped record rather than about a pack.

## Licence

MIT, for the code. See `LICENSE`.

The annex data in `on_the_list/data/` is European Commission material: CosIng,
© European Union, 1995-2026, Annexes II to VI of Regulation (EC) No 1223/2009,
retrieved from the CosIng API and redistributed unmodified. Reuse is governed by
Commission Decision 2011/833/EU; the Commission's legal notice states that
content it owns is licensed under CC BY 4.0.

Nothing in this repository is legal or regulatory advice.
