## Table S9. Robustness of the conflict-atlas tier distribution

Panel (a) breaks the 166 clusters down by kinetic metric. Panel (b) recomputes the tier distribution with every cluster that contains a record from the one source which publishes no DOIs (nanozymenet-k) removed. Panel (c) does the same for Vmax, the weakest extracted field (F1 0.896, Section 3.2). Panels (b) and (c) are the two ways in which the severity structure could have been an artifact of our own weak inputs; in both cases it survives.

**(a) By kinetic metric**

| Metric | Clusters | Consistent | Suspicious | Severe | Severe share | Max fold | Unit-magnitude tag |
|---|---|---|---|---|---|---|---|
| Kₘ | 91 | 15 | 28 | 48 | 52.7% | 419,750 | 3 |
| Vmax | 64 | 8 | 15 | 41 | 64.1% | 3,881,881,882 | 3 |
| kcat | 11 | 3 | 0 | 8 | 72.7% | 3,913,485 | 1 |
| **all metrics** | **166** | **26** | **43** | **97** | **58.4%** | **3,881,881,882** | **7** |

**(b) Excluding every cluster that contains a non-DOI record**

| Set | Clusters | Consistent | Suspicious | Severe | Clusters >= 10⁴x | Clusters >= 10⁶x |
|---|---|---|---|---|---|---|
| all clusters | 166 | 26 | 43 | 97 | 17 | 11 |
| excluding the non-DOI clusters | 153 | 21 | 41 | 91 | 11 | 5 |
| the clusters removed | 13 | 5 | 2 | 6 | 6 | 6 |

**(c) Reading limit of the weakest field**

| Set | Clusters | Severe share |
|---|---|---|
| Kₘ clusters only | 91 | 52.7% |
| Vmax clusters only | 64 | 64.1% |
| all clusters | 166 | 58.4% |

*Reading.* Removing every cluster touched by the no-DOI source costs 6 of the 97 severe clusters and 6 of the 11 clusters at or above 10⁶-fold, but leaves 91 severe clusters standing; restricting to Kₘ alone leaves 48 of 91 severe clusters. The audit's conclusion therefore does not depend on the unverified source or on the weak Vmax field. Generated from `workbench/atlas_out_multi/audit.csv`; thresholds as in Section 5.2 (consistent < 30%, suspicious 30-100%, severe > 100% relative spread).
