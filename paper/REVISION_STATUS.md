# Revision Status and Submission Boundary

## Implemented content revisions

- The paper now uses the two-column IEEE layout.
- The abstract, Introduction, results framing, Discussion, limitations, and
  conclusion distinguish three evidence layers: allocation-only simulation,
  navigation proxy, and closed-loop Gazebo/Nav2 execution.
- Figure 4 is framed solely as a stochastic navigation-proxy result. Its
  AHE--Consensus difference is reported as statistically indistinguishable;
  it is not used as evidence of allocation superiority.
- The matched F45--F58 experiment is framed as evidence for the map-aware ETA
  and bounded-repair configuration, not as evidence for EDPS.
- Four-method physical cells with five seeds are labelled descriptive. The
  text no longer attributes closed-loop differences causally to EDPS.
- The bibliography contains the SciTe-verified Introduction records, and the
  `rostam2024selfadaptive` metadata has been corrected to the DOI record.

## Required experiment before a strong EDPS claim

The current manuscript has no matched physical selector ablation. Run the
full configuration against (i) each fixed paradigm, (ii) no override, and
(iii) no recovery boost, holding all non-selector components fixed. Use common
seeds, a pre-specified primary endpoint, 20--30 seeds per condition, and at
least two maps. Until then, claims about EDPS must remain design claims rather
than physical causal claims.

## RA-L submission blocker

On 2026-07-15 the revised two-column source compiles to 17 pages. The current
RA-L author instructions require six IEEE two-column pages including figures
and references, allow at most two paid extra pages, and therefore cap a Letter
at eight pages. This manuscript is consequently not ready for RA-L submission
in its present form.

To create an RA-L version, retain one method figure, one compact protocol
table, one allocation/proxy result figure, one matched F45--F58 result table,
and one physical-result figure or table. Move exhaustive per-scale tables,
ablation variants, implementation audits, and secondary metrics to a public
data/code repository and cite the artifact. This is a structural condensation
task; it should not be performed by shrinking fonts or margins.
