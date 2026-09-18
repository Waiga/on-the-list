# Limitations

The short version is in the README. This is the detail, for anyone deciding how
far to trust a result.

## The tool answers one question only

*Does a name printed on this ingredient list also appear in Annexes II to VI of
Regulation (EC) No 1223/2009, as the European Commission publishes them?*

It does not answer, and cannot answer:

- Is this product legal to sell in the EU, or anywhere else?
- Is it safe?
- Is the formulation within the limits the annexes set?
- Is the labelling correct?
- Will a retailer or a notification portal accept it?

Those need a regulatory adviser with the formulation in front of them. The
reason the tool is worth anything is that it is honest about the one question it
does answer.

## Absent is not unknown

The distinction the whole design rests on.

Annexes II to VI are lists of restricted substances. Annex II is what may not be
used; III what may be used subject to restrictions; IV, V and VI the permitted
colourants, preservatives and UV filters. **None of them is an inventory of
valid INCI names.** There is no such public list: the INCI dictionary is
published by the Personal Care Products Council and is proprietary.

Aqua and Glycerin appear in none of the five annexes. Not because they are
invalid names, but because nothing restricts them.

So the tool reports ingredients no entry names as **not restricted by these
annexes**, and that phrase is the whole of what it means. There is no `unknown`
verdict, no `unrecognised` category and no spell-check. A tool that treated
annex-absence as a defect would report a false problem on almost every
ingredient of almost every product.

## What the prohibited check can and cannot see

**It sees 314 of Annex II's 1,758 rows, or 17.9%.** The other 1,444 rows identify
their substance by chemical name, CAS number or EC number only, with no entry in
the Common Ingredients Glossary. A label carries INCI names. Where the annex has
no INCI name, there is nothing to compare, and the tool cannot tell you it
missed something.

**Matching is exact, after folding.** Both sides are casefolded, whitespace is
collapsed, dashes are unified, and British spellings of sulphate, sulphite,
sulphide, sulphur, colour and aluminium are folded to the American forms the
INCI convention uses. Nothing else. No stemming, no substring search, no edit
distance. Against a prohibited-substances list a near-match is worse than no
match, because it produces a confident finding about a substance the label does
not contain.

The cost is silent misses: a misspelling, a supplier's trade name, a
transliteration, or a name the Commission happens to write differently will not
match.

**A match on part of a printed name is not reported against Annex II.**
`CI 77288 / CHROMIUM` is a colourant printed beside its element name, and the
fragment `CHROMIUM` matches the Annex II entry for chromium metal. Over 16,635
real labels, fragment matches produced only wrong Annex II findings, so they are
shown under *considered and not counted* instead.

A name with a bracketed aside removed is a different case: `Titanium Dioxide
(nano)` → `Titanium Dioxide` is still the name of the ingredient, and does
match. Whether it is depends on how much of the name survives. The part outside
the brackets must be at least half the words. `Citrus Limon (Lemon) Peel Oil`
keeps four of five and is the name; `Styrene (Acrylate Copolymer)` keeps one of
three and is a fragment, and it matched the styrene monomer in Annex II until
the rule was written down. The same test applies either way round, so `Chromium
(CI 77288)` and `CI 77288 / CHROMIUM` now get the same answer; before, one was
reported as prohibited and the other was not.

**This narrowing is Annex II's alone.** The warning-wording check, the position
check and the coverage count all accept a match found on a bracketed or
slash-separated part of a printed name, and the finding does not say so. That
is deliberate, because it is the only way `CI 77891` is found inside `Titanium
Dioxide (CI 77891)`, but it means "exact names only" is true of the prohibited
check and not of the whole tool.

**A conditional entry is reported in its own group.** Many Annex II entries are
prohibitions with a condition attached in the Commission's own wording:
"except if the full refining history is known", "when used as a substance in
hair dye products", "if it contains > 0,1 % w/w Butadiene", "(nano)". An
ingredient list states none of those things. The tool detects the condition
lexically, looking for *except*, *unless*, *when used*, *other than*, *with
the exception of*, *only if*, *only when*, *provided that* and a bare *if* in
the entry's own chemical name. It puts those findings after the unconditional
ones, and prints the entry's wording so a reader can settle it. It never decides
whether the condition is met.

**A nanomaterial entry whose own INCI names do not say nano is not reported.**
Annex II entry 1725 is `Styrene/Acrylates copolymer (nano)` and its
identified-ingredients column reads `STYRENE/ACRYLATES COPOLYMER`, with no nano
marker. 416 labels in the corpus print the ordinary polymer. Those are shown
under *considered and not counted*, with the reason, rather than reported.

**The known false positive.** Annex II entry 1388 is
`Octamethylcyclotetrasiloxane; D4`, and its identified-ingredients column gives
`CYCLOMETHICONE`. Cyclomethicone is the INCI name of a *mixture* of cyclic
siloxanes; a label printing it has not said the product contains D4. 99 of the
1,066 unconditional findings in the corpus run are this. No mechanical signal
separates it from a correct match, and inventing an exception list for it would
be tuning the tool against the one corpus it was measured on. It is left in and
written down.

## What the position check can and cannot mean

Article 19(1)(g) of Regulation (EC) No 1223/2009 requires ingredients in
descending order of weight, and adds that colourants other than hair colourants
**may** be listed in any order after the other ingredients.

That is a permission, not a requirement. A colourant listed in weight order,
early in the list, is not obviously out of place. Most lists put colourants
last, so a colourant in the middle is worth a look. The finding is still only a
statement about where a name is printed, and the report says so in those words.

Three further caveats, printed with every finding:

- **Hair colourants are outside the derogation.** On a hair dye, the position
  proves nothing at all.
- **Ingredients below 1% may be listed in any order**, colourant or not.
- **The "may contain" block is not examined.** It is printed across a whole
  shade range, so its order carries no information and its contents may not be
  in the unit in your hand.

Only bare `CI NNNNN` forms trigger the check, plus the `CI NNNNN:N` lake suffix
and the `Cl NNNNN` that scanners produce for it. Named Annex IV substances are
not used: Titanium Dioxide is an Annex IV colourant, an Annex VI UV filter and
an opacifier, and where it sits proves nothing about which job it is doing.

The finding names the annex entries the register actually holds for that colour
index number, which is not always Annex IV: CI 12150, CI 20170, CI 27290 and CI
45425 are in Annex II only, each prohibited in hair dye products.

Measured on 30 hand-audited findings: 4 wrong. Two are pack prose the parser
kept, one is a make-up palette declaring several shades in one field, and one is
an OCR'd label whose text before the word `INGREDIENTS` is unreadable.

## What the repeated entry audit found

A fresh row level audit of the same seeded sample found 21 false positives and
9 findings that correctly described a repeated normalized name in the
historical recorded text. This is a result for 30 sampled findings. It is not a
population rate for the 16,635 label corpus, all repeated entry findings, clean
single product lists, or future inputs.

The 21 false positives comprised nine multi product or multi component fields,
seven OCR, transcription, or parser artifacts, and five fields that were not
one cosmetic ingredient declaration.

The tool detects this when the pack prints a heading it can recognise: a short
label ending in a colon that is not itself an ingredient-list preamble or a
warning-panel word, or a second `Ingredients:`. When it finds one, it says so
and does not run either order-dependent check. On the corpus it flagged 1,631 of
16,635 labels that way.

It cannot detect a component boundary the pack does not print. Several
heuristics were tried and each either missed almost as much or suppressed real
findings; none is in the tool.

Several sound rows did not have a usable package image. They are sound against
the historical recorded text, not visually confirmed on pack. Two sound rows
are different barcodes with the same recorded formula, so they are not
independent formulations. One sound row is boundary sensitive because its
second occurrence is inside a supplier blend. That row supports the literal
repeated normalized name statement, not a formulation duplication claim.

The [row level audit](audits/repeated-entry-audit.md) records the judgment and
evidence basis for every finding.

## Why the warning check looks for so little

The "Wording of conditions of use and warnings" column of Annexes III to VI
mixes two unrelated things: text that must be printed on a label, and conditions
that have nothing to do with a label at all. Both are in the same cell, in
prose, with no marker separating them:

> Purity criteria as set out in Commission Directive 95/45/EC (E 129)

> Only nanomaterials having the following characteristics are allowed: purity
> ≥ 99 %, rutile form …

> Not to be used in applications that may lead to exposure of the end-user's
> lungs by inhalation

None of those is label text. Searching a pack for them would report a missing
warning on every sunscreen containing zinc oxide.

So the tool extracts one shape only: a `Contains …` statement, at the start of a
line or after a short qualifier ending in a colon on that same line. That yields
38 of the 627 entries in Annexes III to VI and 35 distinct statements. Every
other wording is reported to the reader verbatim, labelled as attached but not
searched for.

An earlier version also pulled quoted passages out, because the annexes quote
the long hair-dye warnings. It was abandoned: the annexes use apostrophes as
quotation marks, the quoted text contains apostrophes and inner quotes around
"black henna", and the extractor produced fragments like `tattoo in the past`.

Even within that narrow shape, a statement may be conditional. Annex III entry 4
reads "Above 2%: Contains ammonia"; Annex VI entry 4 footnotes Benzophenone-3 as
not required at 0,5 % or less. An ingredient list states no concentration, so
the tool prints the entry's full wording with every finding and leaves the
condition to the reader.

**A gap is not a violation.** The wording may be printed on a part of the pack
the supplied text does not cover, or in another language, or the entry may not
apply to this product type. The check reports a difference between two documents
and says so in the finding itself.

**Its accuracy is unmeasured.** Open Beauty Facts carries no field holding what
is printed on a pack, so the corpus run establishes only that the check fires on
the right population, not that it is right.

## Where a finding can come from bad input rather than a bad label

A quarter of the corpus, 4,288 of 16,635 labels, had at least one parsed
"ingredient" longer than any INCI name, meaning pack prose ended up inside the
panel: a warning, a distributor address, a second product's list, a batch code.
The tool says so in a limits line when it happens, and every count in that
report is affected.

Other routes:

- **A truncated panel.** The tool checks what it was given and cannot know the
  rest existed.
- **OCR damage.** `Cl` for `CI`, `ct 42051`, `CI 074260`, a comma inserted into
  the middle of a name. Some of these are handled; more are not.
- **Crowd-sourced data.** In the measurement, a finding may be about a mistyped
  record rather than about a pack.

## What the offline promise does and does not cover

Nothing on the analysis path can import a module that opens a connection or
starts a process; a test reads the source and refuses one, and a second test
runs a real analysis with `socket.socket` replaced by something that raises.

What neither can see is **the filesystem**. Reading files is the whole job, so
`pathlib` and `open` are allowed, and no static read can tell a local path from
a network one. `--register` accepts any path, so a UNC path, an SMB or NFS
mount, or a FUSE filesystem reaches the network with no socket call in this
package's own source. That is a real gap and it is written down here and in the
test's own docstring rather than left to be discovered.

## Scope

Five annexes of one Regulation, as published on one date. Not read: Annex I (the
safety report), Annex VII, the CosIng ingredient database itself, SCCS opinions,
national requirements, retailer standards, or anything outside the EU. The
register the report cites is dated, hashed and re-downloadable, so a stale
result is detectable rather than invisible.

## Data and licensing

The annex CSVs in `on_the_list/data/` are the Commission's own export,
redistributed byte for byte: CosIng, © European Union, 1995-2026. Reuse is
governed by Commission Decision 2011/833/EU, and the Commission's legal notice
states that content it owns is licensed under CC BY 4.0. Their SHA-256 hashes
are in `on_the_list/registry_manifest.py` and a test fails if a file and its
hash disagree.

The 16,635-label corpus used for the measurements is an Open Beauty Facts
export. That database is ODbL 1.0, attribution and share-alike, which is
incompatible with redistributing a filtered subset inside an MIT repository. The
corpus is not included here; only the measurements are, with the export's own
hash so the same file can be obtained. See `docs/corpus-manifest.md`.
