# QIIME2 and PICRUSt2 QC checklist

Use this checklist before a local FRB rerun. Record final decisions in `config/frb.toml` and in a dated run note.

## Run information

- Dataset:
- Configuration file:
- Raw FASTQ directory:
- QIIME2 output directory:
- Reviewer:
- Date:

## 1. Manifest and metadata

- [ ] `manifest.tsv` includes every intended sample.
- [ ] `metadata.tsv` assigns every sample to the correct group.
- [ ] No sample is assigned to `unknown` unless this is intentional and documented.
- [ ] FASTQ filenames, sample IDs, and configured sample names agree.

Record: `[groups]`, `project.raw_dirname`, and `project.qiime_dirname`.

## 2. Demultiplexed-read quality

- [ ] Forward-read quality remains adequate through the chosen truncation position.
- [ ] Reverse-read quality remains adequate through the chosen truncation position.
- [ ] The retained reads provide sufficient paired-end overlap.
- [ ] Samples with unusually few reads are documented.

Record: `qiime2.dada2.trim_left_f`, `trim_left_r`, `trunc_len_f`, `trunc_len_r`, and `n_threads`.

## 3. DADA2 output

- [ ] Most samples retain adequate reads after filtering, merging, and chimera removal.
- [ ] Samples with unusually low non-chimeric retention are documented.
- [ ] Any sample exclusion has a technical rationale.

Decision:

- [ ] Retain all samples.
- [ ] Exclude documented samples.
- [ ] Revise trimming or truncation and rerun DADA2.

## 4. Feature filtering

- [ ] The feature-frequency distribution was inspected.
- [ ] `min_frequency` does not remove plausible biological signal excessively.
- [ ] `min_samples` retains features relevant to the group-level analysis while limiting likely noise.

Record: `qiime2.feature_filter.min_frequency` and `min_samples`.

## 5. Taxonomy

- [ ] The classifier and reference-database versions are recorded.
- [ ] Phylum-, family-, and genus-level summaries are plausible.
- [ ] Unassigned or ambiguous taxa are not unexpectedly prevalent.
- [ ] `table-genus.tsv` was exported for the Python workflow.

## 6. Rarefaction

- [ ] `alpha-rarefaction.qzv` was inspected.
- [ ] Sampling depth retains sufficient samples in each group.
- [ ] Diversity curves are stable around the selected sampling depth.

Record: `qiime2.rarefaction.sampling_depth`.

## 7. PICRUSt2

- [ ] PICRUSt2 completed without failed samples.
- [ ] NSTI distributions were inspected before applying an NSTI filter.
- [ ] Any NSTI threshold is recorded in the configuration.
- [ ] `path_abun_unstrat.tsv.gz` and `path_abun_contrib.tsv.gz` exist.

## 8. Final Python analysis

- [ ] `python scripts/run_analysis.py --config config/frb.toml ...` completed.
- [ ] Three-group outputs exist: `genus_stats_3group.tsv`, `TOP_genus_3group.tsv`, `pathway_stats_3group.tsv`, and `TOP_pathways_3group.tsv`.
- [ ] The output directory and configuration are recorded together.
