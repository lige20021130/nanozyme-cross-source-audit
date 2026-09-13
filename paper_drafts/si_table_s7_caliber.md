## Table S7. Comparison-rule sensitivity of the 100-paper agreement

The same 100 papers (102 DOI-level matches on the database side) scored twice: once with the three representation normalisations used throughout this work (*normalised*), and once verbatim, comparing field values as written (*verbatim*). Only three fields can differ; the remaining fourteen are identical under both rules, which is why the two aggregate values bracket the result rather than contradicting it.

| Metric | Human side, normalised | Human side, verbatim | Database side, normalised | Database side, verbatim |
|---|---|---|---|---|
| pooled field-level F1 | 0.907 | 0.847 | 0.907 | 0.907 |
| pooled precision | 0.869 | 0.768 | 0.891 | 0.891 |
| pooled recall | 0.949 | 0.943 | 0.924 | 0.924 |
| macro-F1 over compared fields | 0.902 | 0.810 | 0.904 | 0.904 |
| pooled field accuracy | 0.830 | 0.734 | 0.831 | 0.831 |
| mean per-paper macro-F1 | 0.841 | 0.742 | 0.843 | 0.843 |

Field-level detail for the three fields that differ (`tp` / `fp` / `fn` counts, then F1):

| Field | Human, normalised | Human, verbatim | Database, normalised | Database, verbatim |
|---|---|---|---|---|
| Metal identity (`metal_type`) | 146 / 16 / 3 → 0.939 | 0 / 162 / 3 → 0.000 | n/a — not stored by the databases | n/a — not stored by the databases |
| Morphology (`shape`) | 147 / 11 / 7 → 0.942 | 40 / 118 / 7 → 0.390 | n/a — not stored by the databases | n/a — not stored by the databases |
| Particle size (`size_nm`) | 90 / 35 / 23 → 0.756 | 77 / 48 / 23 → 0.684 | n/a — not stored by the databases | n/a — not stored by the databases |

The three fields below are absent from the public-database records, so the database columns of this table are compared over the six fields that the databases do carry (material, mimicked activity, pH, temperature, Kₘ, Vmax).

The three normalisations, stated exactly as implemented (`workbench/cross_validate.py`, `_records_match`):

1. **Metal identity** — an element symbol and its atomic number are treated as one annotation: both sides are converted to the atomic number before comparison (`Pd` ↔ 46). Under verbatim comparison this field scores 0 by construction, because gold stores symbols (1,038 string values) and the pipeline stores numbers (353 integer values).
2. **Morphology** — a generic annotation is not charged against a more specific prediction: if either side is one of {`nanoparticle`, `polyhedral`, `particle`}, the pair matches; otherwise a substring test applies (`nanocube` ⊂ `hollow nanocube`). This rule carries weight, because the gold morphology column is generic in 611 of 1,057 rows (58%). It is a tolerance policy, not a notation equivalence, and is therefore reported explicitly rather than folded into a single score.
3. **Particle size** — relative tolerance widened from 10% to 30%, matching the spread of TEM and XRD reporting conventions.

Fields *not* listed above are compared verbatim under both rules. The verbatim column is the conservative bound; the normalised column is the figure used in Section 3.4 because it is the caliber under which the 67-paper gold evaluation of Section 3.2 is also scored.
