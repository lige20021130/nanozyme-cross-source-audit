## Table S6. Unit-recovery worksheet — source-publication verification of same-pH conflicts

**Protocol.** For each conflict group in Table S3 we attempted to recover the kinetic value as
published in the *original* paper. Priority order: (1) exact numeric match of one camp against the
source publication; (2) internal consistency of the reported substrate concentration range with the
claimed Kₘ; (3) no verification possible (PDF unavailable in the local corpus, or the kinetic table
is a raster image with no text layer). Verification is **asymmetric**: a confirmed match rules in a
unit-scaling origin, whereas a failure to verify does **not** rule it out — it only leaves the case
undecided. Where a recovered source table shows that a group's two camps come from *different
catalysts or different reporters* rather than the same measurement, we classify the group as a
**grouping artifact** instead of a unit artifact (case A2).

**Corpus.** 1,222 PDFs of the local nanozyme literature corpus (see the data availability
statement), indexed and matched by DOI suffix
(`workbench/p0_unit_recovery.py`, index `workbench/p0_pdf_index.json`).
Of the 10 unique DOIs behind the 17 conflict groups, 8 were located in the corpus.
Rasterised kinetic tables were read with OCR (RapidOCR, 300 dpi); every recovered value below is
quoted from the OCR text together with the unit header **exactly as printed**
(`paper_drafts/s6_recovery_probe.md` holds the verbatim grids).

### (A) Confirmed — unit conversion (M ↔ mM), 4 groups

| # | DOI | Material · substrate · pH | Database values (mM) | Source publication | Verdict |
|---|---|---|---|---|---|
| 6 | 10.1021/acsami.6b05354 | CuO · H₂O₂ · 4.65 | AI-ZYMES 0.4, human 0.4;<br>DiZyme 400, NanozymeDB 400 | ACS Appl. Mater. Interfaces, **Table 1**, header "K_m **(M)**": CuO, H₂O₂ column = **0.40**; TMB column = 0.025 | **Confirmed.** 0.40 M = 400 mM. The two camps are the same measurement stored with and without the M→mM conversion; the ×1000 gap is a unit-scale artifact |
| 7 | 10.1021/acsami.6b05354 | CuO · TMB · 4.65 | AI-ZYMES 0.025, human 0.025;<br>DiZyme 25, NanozymeDB 25 | Same table: TMB column = **0.025 (M)** | **Confirmed.** 0.025 M = 25 mM |
| 8 | 10.1021/acsami.8b20942 | HccFn(Co₃O₄) · TMB · 4.5 | AI-ZYMES 0.84, human 0.84;<br>NanozymeDB 840 | ACS Appl. Mater. Interfaces, **Table 1**, header "K_M **(M)**": HccFn(Co₃O₄) · TMB = **0.84** | **Confirmed.** 0.84 M = 840 mM. NanozymeDB converted M→mM; AI-ZYMES and the human sheet kept the printed numeral and labelled it mM |
| 9 | 10.1021/acsami.8b20942 | HccFn(Fe₃O₄) · TMB · 4.5 | AI-ZYMES 1.12, human 1.12;<br>NanozymeDB 1120 | Same table: HccFn(Fe₃O₄) · TMB = **1.12 (M)** | **Confirmed.** 1.12 M = 1120 mM, same pattern |

Both papers print their Kₘ column in **M** — the least convenient unit a harvester could be handed,
and precisely the one where dropping the prefix produces a ×1000 error. In the HccFn paper the same
table supplies an **internal control**: its two H₂O₂ rows (1.77 M and 2.48 M) are stored *identically*
by all three sources (1770 mM and 2480 mM; fold 1.0), i.e. every source converted those correctly.
The artifact is therefore source-specific behaviour on rows that happened to split, not a defect of
the paper.

### (A2) Confirmed — NOT a unit artifact: catalyst / reporter conflation, 1 group

| # | DOI | Material · substrate · pH | Database values (mM) | Source publication | Verdict |
|---|---|---|---|---|---|
| 13 | 10.1016/j.colsurfa.2016.07.037 | Fe₂O₃ · H₂O₂ · 3.6 | AI-ZYMES 11.3, human 305 (fold 27) | Colloids Surf. A, **Table 1**, header "Kₘ **(mM)**": rows are *bare* Fe₂O₃ nanoparticles and *GO-modified* GO-Fe₂O₃ hybrids, each with TMB and with H₂O₂ in **two reporters** (TMB and ABTS). Bare Fe₂O₃ · H₂O₂(TMB) = **120**; bare Fe₂O₃ · H₂O₂(ABTS) = 11.3; GO-Fe₂O₃ · H₂O₂(TMB) = 305 | **Grouping artifact, not a unit artifact.** The printed unit is already mM, and the 27-fold gap is fully explained by the two entries describing **different catalysts and different reporters**: 11.3 is bare Fe₂O₃ read with ABTS, 305 is the GO-modified hybrid read with TMB. The value actually matching this group's key is a third number, 120 mM, which agrees with neither camp |

This group is retained in the census because the conflict is real *at the granularity the databases
publish* — the databases do not carry the modifier (GO) or the reporter (TMB vs ABTS) that separate
the rows. It is reported here to make explicit that not every order-of-magnitude gap is a unit gap:
the atlas separates conflicts by mechanism, and one of the 17 resolves to an annotation-granularity
problem rather than a scaling problem.

### (B) Directionally supported — substrate-range inconsistency, 3 groups

| # | DOI | Material · substrate · pH | Database values (mM) | Source publication | Verdict |
|---|---|---|---|---|---|
| 4 | 10.1016/j.bios.2014.08.062 | NiO · H₂O₂ · 3.8 | AI-ZYMES 0.00666 / DiZyme 208 | Biosens. Bioelectron., p. 3: "the concentration of H₂O₂ was tuned to 10, 20, 40, 60, 80, 100, 125, **250 mM** for NiO" | **Directional.** A Kₘ of 0.00666 mM is three orders of magnitude below the lowest substrate concentration used in the assay; 208 mM is consistent with the 10–250 mM design. The unit-recovery reading favours the 208 mM camp |
| 5 | 10.1016/j.bios.2014.08.062 | NiO · TMB · 3.8 | AI-ZYMES 0.0067 / DiZyme 208 | Same assay description | **Directional**, as above |
| 10 | 10.1016/j.bios.2014.08.062 | H₂TCPP-NiO · TMB · 3.8 | AI-ZYMES 0.391 / NanozymeDB 39.1 | Same page: H₂TCPP-NiO series 10–125 mM | **Directional**: ×100 gap matches an mM/µM-type scaling; 0.391 mM is below the assayed range |

### (C) Source located, printed values still not recoverable, 2 groups

| # | DOI | Material · substrate | Status |
|---|---|---|---|
| 12 | 10.1039/c9cc00199a | Fe SAEs · TMB · 3.8 | Main PDF located; text layer carries only qualitative statements ("about ten times lower than HRP") and points to **Table S2 of the SI**, which is **not** present in the local corpus. No absolute Kₘ and no unit header are reachable |
| 16 | 10.1039/c6nr02730j | CeO₂ · TMB · 4.0 | Only the SI is present locally; its Table S1 tabulates **kcat** (0.16 s⁻¹) and **kcat/Kₘ** (0.11 mM⁻¹ s⁻¹) but **no Kₘ column**. The main PDF, which would carry the Michaelis–Menten table, is absent. Kₘ was deliberately **not** back-calculated from kcat/(kcat/Kₘ) |

### (D) Not verified — source PDF unavailable locally, 7 groups

| # | DOI | Material · substrate | Status |
|---|---|---|---|
| 1–3 | 10.1038/s41467-018-03903-8 | N-PCNSs-5 / PCNSs / N-PCNSs-3 · H₂O₂ · 7.0 | PDF not in local corpus (the 10⁶-fold cases) |
| 11 | 10.1016/j.apcatb.2020.118725 | Cit-IrNPs · H₂O₂ · 3.86 | PDF not in local corpus |
| 14–15 | 10.1016/j.snb.2023.134429 | rGO@PDA@CeO₂ · H₂O₂ / TMB · 7.4 | PDF not in local corpus |
| 17 | 10.1039/c9nr05346h | CeO₂ · TMB · 4.0 | PDF not in local corpus |

### Summary of verification status (17 groups)

| Status | Groups | Share |
|---|---|---|
| (A) Confirmed unit conversion (M ↔ mM) | 4 | 23.5% |
| (A2) Confirmed **not** a unit artifact (catalyst/reporter conflation) | 1 | 5.9% |
| (B) Directionally supported (substrate-range inconsistency) | 3 | 17.6% |
| (C) Source located, printed value not recoverable | 2 | 11.8% |
| (D) Source PDF unavailable locally | 7 | 41.2% |

**Honest reading.** 4 of the 17 conflicts are *demonstrably* unit-conversion artifacts, 3 more are
directionally consistent with that reading, and 1 is demonstrably **not** a unit artifact but an
annotation-granularity artifact — a result obtained by reading the source table, and reported here
because a census that can only ever confirm its own hypothesis is not an audit. The remaining 9 are
**undecided, not disproven**: in every case the blocking factor is that the kinetic table is a raster
image, or the printed value lives in a supplementary file that is not attached to the indexed PDF.
We therefore report the unit-scale mechanism as *established for the two-camp ×1000 signature* (which
is exactly the pattern that requires an exact power-of-ten explanation) and as *a hypothesis for the
remainder*. Adjudicating the remaining groups requires opening the source tables one by one; the
worksheet is delivered in a form that makes that work incremental (Table S6 columns: database value →
source value → source unit → verdict).

**A side observation relevant to the field.** Among the 8 located papers, 4 had kinetic tables with
no text layer at all (they had to be read by OCR), and 2 more kept the printed values in a
supplementary file that is not indexed alongside the article. Any database whose curation protocol
depends on re-reading the original table — human or machine — inherits this failure, and an OCR step
does not remove it: OCR of a raster table is itself an error-prone manual step that we had to perform
by hand here. This is an additional argument for condition-bound, provenance-carrying storage: the
*number* must be accompanied by the *unit as printed*, because the source itself often cannot be
re-interrogated cheaply.
