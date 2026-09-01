# Data and code availability

This repository stores analysis code, configuration files, documentation, and the lightweight processed CSV datasets required to reproduce the primary FRB Figures 4 and 5. It does not store raw sequencing reads, QIIME2 artifacts, PICRUSt2 intermediate files, complete generated result tables, or figure exports outside the versioned release asset.

## Public release policy

Before citing this repository, archive a fixed GitHub release in Zenodo or another long-term repository and replace the placeholders below with permanent identifiers.

- Code repository: `https://github.com/Yuki-Saito-UOS/frb-16s-picrust2-analysis`
- Archived code concept DOI: [`10.5281/zenodo.22227745`](https://doi.org/10.5281/zenodo.22227745)
- Prior archived code version DOI (`v0.2.0`): [`10.5281/zenodo.22227746`](https://doi.org/10.5281/zenodo.22227746)
- Raw 16S rRNA sequencing reads: not publicly released with this code archive.
- Public processed figure datasets: `data/processed/`

## Files intentionally excluded from Git

- Raw FASTQ files.
- QIIME2 artifacts and visualizations: `*.qza`, `*.qzv`.
- PICRUSt2 outputs, including compressed contribution tables.
- Generated statistical tables in `results/`, except the curated figure-reproduction CSV files in `data/processed/`.
- Generated figure exports in `figures/`.
- Local annotation caches.

## Reproducibility boundary

The repository is sufficient to reproduce the displayed Figure 4 and Figure 5 values from the processed CSV files. Rerunning the complete computational workflow requires the raw sequencing data and QIIME2/PICRUSt2 inputs. Sequencing and library-preparation details are documented in `docs/main_figures_methods_and_legends.md`; raw sequencing files and individual-level metadata are not included and are not part of this public release.

## Public disclosure check

Do not publish the repository release until all of the following are true.

- The study authors and collaborators have approved public release.
- Raw sequencing data have been deposited or an approved access restriction is documented.
- No patient-identifying, collaborator-private, unpublished non-target project, or internal laboratory-only material is present.
- All public claims and figure definitions match the approved study record.
