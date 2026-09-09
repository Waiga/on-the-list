# Examples

Two invented labels. Nothing here is a real product, a real brand, or a real
formulation: the ingredient lists were written to exercise the checks, and the
substances in them are named in the published annexes so that every finding can
be traced back to a public document.

```bash
on-the-list examples/shade-stick.txt              # findings, exit 1
on-the-list --ingredients examples/plain-cream-inci.txt \
            --pack-text examples/plain-cream-pack.txt   # nothing found, exit 0
```
