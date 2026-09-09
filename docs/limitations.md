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
invalid names — because nothing restricts them.

So the tool reports ingredients no entry names as **not restricted by these
annexes**, and that phrase is the whole of what it means. There is no `unknown`
verdict, no `unrecognised` category and no spell-check. A tool that treated
annex-absence as a defect would report a false problem on almost every
ingredient of almost every product.

## What the prohibited check can and cannot see

**It sees 314 of Annex II's 1,758 rows — 17.9%.** The other 1,444 rows identify
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

**A match on part of a printed name is not reported.** `CI 77288 / CHROMIUM` is
a colourant printed beside its element name, and the fragment `CHROMIUM` matches
the Annex II entry for chromium metal. Over 16,635 real labels, fragment matches
produced only wrong findings, so they are shown under *considered and not
counted* instead. A name with a bracketed aside removed — `Titanium Dioxide
(nano)` → `Titanium Dioxide` — is still the name of the ingredient, and does
match.

**A conditional entry is reported in its own group.** Many Annex II entries are
prohibitions with a condition attached in the Commission's own wording:
"except if the full refining history is known", "when used as a substance in
hair dye products", "if it contains > 0,1 % w/w Butadiene", "(nano)". An
ingredient list states none of those things. The tool detects the condition
lexically — it looks for *except*, *unless*, *when used*, *other than*, *with
the exception of*, *only if*, *only when*, *provided that* and a bare *if* in
the entry's own chemical name — puts those findings after the unconditional
ones, and prints the entry's wording so a reader can settle it. It never decides
whether the condition is met.

**A nanomaterial entry whose own INCI names do not say nano is not reported.**
Annex II entry 1725 is `Styrene/Acrylates copolymer (nano)` and its
identified-ingredients column reads `STYRENE/ACRYLATES COPOLYMER`, with no nano
marker. 421 labels in the corpus print the ordinary polymer. Those are shown
under *considered and not counted*, with the reason, rather than reported.

**The known false positive.** Annex II entry 1388 is
`Octamethylcyclotetrasiloxane; D4`, and its identified-ingredients column gives
`CYCLOMETHICONE`. Cyclomethicone is the INCI name of a *mixture* of cyclic
siloxanes; a label printing it has not said the product contains D4. 101 of the
1,074 unconditional findings in the corpus run are this. No mechanical signal
separates it from a correct match, and inventing an exception list for it would
be tuning the tool against the one corpus it was measured on. It is left in and
written down.

## What the position check can and cannot mean

Article 19(1)(g) of Regulation (EC) No 1223/2009 requires ingredients in
descending order of weight, and adds that colourants other than hair colourants
**may** be listed in any order after the other ingredients.

That is a permission, not a requirement. A colourant listed in weight order,
early in the list, is not obviously out of place. Most lists put colourants
last, so a colourant in the middle is worth a look — but the finding is a
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

Measured on 30 hand-audited findings: 3 wrong, all of them a colour index number
the source record's OCR had mangled into something the tool read as an ordinary
ingredient.

## Why the repeated-entry check is the weakest one

Measured on 30 hand-audited findings: **15 wrong.**

Every failure had the same cause. The ingredient field held more than one
product's list — a hair colour kit's crème and developer, a gift set's shower
gel and eau de toilette, a mouthwash's drug-facts panel. An ingredient appearing
once in each component is not a repeated ingredient.

The tool detects this when the pack prints a heading it can recognise: a short
label ending in a colon that is not itself an ingredient-list preamble or a
warning-panel word, or a second `Ingredients:`. When it finds one, it says so
and does not run either order-dependent check. On the corpus it flagged 1,654 of
16,635 labels that way.

It cannot detect a component boundary the pack does not print, which is the
common case. Several heuristics were tried and each either missed almost as much
or suppressed real findings; none is in the tool.

On a single product's own ingredient list — which is what the tool is for — the
check is sound. All fifteen correct findings in the audited sample were
single-product lists. The corpus figure is still the honest one, because a user
cannot be assumed to know which kind of input they have.

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

A quarter of the corpus — 4,309 of 16,635 labels — had at least one parsed
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
export. That database is ODbL 1.0 — attribution and share-alike — which is
incompatible with redistributing a filtered subset inside an MIT repository. The
corpus is not included here; only the measurements are, with the export's own
hash so the same file can be obtained. See `docs/corpus-manifest.md`.
