# Repeated entry audit

Date checked: 11 September 2026

This page records the human judgments for the seeded sample of repeated entry
findings described in the [corpus manifest](../corpus-manifest.md). The automated
script selected the sample. Human review produced the judgments.

## Source and method

1. Historical Open Beauty Facts export SHA256:
   `d527f033d2549b86424db0ef1e87b785f92f53901036afd0c0a24bd629a766a5`
2. Seeded sample SHA256:
   `1bda12783a390a8e1e4a31cbe5323562118e4730352427a69c87b63234d1d43f`
3. Sample method: seed 11, one row per barcode, 30 repeated entry findings.
4. Review basis: the ingredient text in the pinned historical export and the
   historical package image revisions that were available for review.

The live Open Beauty Facts record can change. Current API state was not used to
revise the historical classifications below.

## Result

1. False positives: 21
2. Sound findings: 9
3. Unresolved: 0

The sound findings correctly described a repeated normalized name in the
historical recorded text. Sound does not mean that every row was visually
confirmed on a package image. This is a result for this sample. It is not a
population rate.

## Row level ledger

| Row | Barcode | Finding | Judgment | Reason and evidence basis |
|---:|---|---|---|---|
| 1 | 3474636975853 | Benzyl Alcohol | Sound | The historical single product list records the name twice. No usable label image was available. |
| 2 | 3600542341530 | Tocopherol | False positive | The occurrences sit in different parts of a hair colour pack. |
| 3 | 3178040690912 | Sels de Sodium | False positive | The shared words qualify two different declared fatty acid compounds. |
| 4 | 00541190 | Coumarin | False positive | The package image prints it once. Damaged source text loops part of the list. |
| 5 | 0811913015209 | Citral | Sound | The historical single product record contains the name twice. The available image was not legible enough to confirm it visually. |
| 6 | 7702031311218 | Hydroxycitronellal | False positive | The pinned historical export records the name twice. The exact [historical image revision](https://images.openbeautyfacts.org/images/products/770/203/131/1218/ingredients_en.4.400.jpg) prints it once, so the repeated text is an export artifact. |
| 7 | 8001841713373 | Trideceth 10 | False positive | The package image prints it once. The source text repeats a damaged tail segment. |
| 8 | 3600521987704 | Cetearyl Alcohol | False positive | The occurrences cross three hair colour components. |
| 9 | 8908025697071 | Carbomer | False positive | The package image prints it once. The source text repeats a damaged block. |
| 10 | 3600523759255 | Cetearyl Alcohol | False positive | The occurrences cross colour cream, developer, shampoo, and mask components. |
| 11 | 7332531073127 | Aqua | False positive | The occurrences begin separate colour, developer, and aftercare formulas. |
| 12 | 8480000469786 | Coco Glucoside | False positive | The package image prints it once. The source record duplicates it. |
| 13 | 3600523806881 | Cetearyl Alcohol | False positive | The occurrences cross colour cream, developer, and aftercare components. |
| 14 | 3474630006850 | Propylene Glycol | False positive | The field is an alphabetical ingredient glossary, not one product declaration. |
| 15 | 5901018021122 | Cetyl Esters | False positive | The package image prints it once. The source record duplicates it and repeats a later block. |
| 16 | 5694230442683 | Ecocert | False positive | Ecocert appears in English and French certification prose after the ingredient list. |
| 17 | 3282779053266 | Glyceryl Linoleate | Sound | The historical single product record contains the name twice. No usable image was available. |
| 18 | 5703147061099 | Cetearyl Alcohol | False positive | The occurrences cross developer and aftercare components. |
| 19 | 5904917482346 | Squalane | Sound | The package image visibly prints the name twice in one list. |
| 20 | 3600531384173 | Phenyl Trimethicone | Sound | The historical single product record contains the name twice. No usable image was available. |
| 21 | 0022400528434 | Sodium Chloride | False positive | The occurrences sit in separately headed shampoo and conditioner lists. |
| 22 | 3660749040582 | Sodium Laureth Sulphate | Sound | The recorded declaration contains the normalized name once alone and once inside a supplier blend. This supports only the literal repeated name claim. |
| 23 | 4010355218919 | Limonene | False positive | The occurrences sit in English and German versions of the same declaration. |
| 24 | 0194346188659 | FD | False positive | The parser split distinct FD and C colour names at punctuation. The field is a food supplement record. |
| 25 | 3600531384128 | Phenyl Trimethicone | Sound | The historical single product record contains the name twice. It matches the formula in row 20. No usable image was available. |
| 26 | 3600523591831 | 2 | False positive | The parser created the fragment from distinct names including Diglyceryl Polyacyladipate 2 and Steareth 2. |
| 27 | 5703147061020 | Linalool | False positive | The occurrences cross colour gel and aftercare formulas. |
| 28 | 0745114958075 | Acide Hyaluronique | Sound | The historical single product record contains the name twice. The available image was too blurred to confirm it visually. |
| 29 | 3574660569728 | Propylene Glycol | Sound | The package image visibly prints the name twice in one list. |
| 30 | 3600541237575 | Steareth 20 | False positive | The occurrences cross colour cream and developer formulas. |

## False positive groups

1. Nine multi product or multi component fields.
2. Seven OCR, transcription, or parser artifacts.
3. Five fields that were not one cosmetic ingredient declaration.

## Limits

1. Several sound rows do not have a usable ingredient image. They are sound
   against the historical recorded text, not visually confirmed on pack.
2. Rows 20 and 25 are different barcodes with the same recorded formula. They
   are not independent formulations.
3. Row 22 is boundary sensitive because the second occurrence is inside a
   supplier blend. The narrow repeated normalized name statement is supported.
   A formulation duplication claim is not.
4. The result must not be generalized beyond this sample.

## Data attribution and licence

The source database is Open Beauty Facts. The historical export is identified
above so the reviewed snapshot can be distinguished from later database changes.
The Open Beauty Facts database is available under the Open Database Licence 1.0.
The corpus is not included in this repository.

The repository code remains available under its [MIT licence](../../LICENSE).
The code licence does not replace the source database attribution or terms.
