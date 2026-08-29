# Reproducible FRB 16S rRNA Predicted-Metagenome Analysis

This repository contains the public computational workflow for fecal 16S rRNA and PICRUSt2 predicted-metagenome analyses of control (Ctrl), rice bran (RB), and fermented rice bran (FRB) groups. The scope is limited to the FRB 16S/PICRUSt2 analysis and its primary community-composition and predicted-function outputs.

## Public contents

- QIIME2/PICRUSt2 workflow code and configuration.
- Anonymized processed CSV files used for the primary outputs.
- Methods, figure definitions, and data-availability information.
- Vector PDF of the two primary figures attached to the GitHub release.

Raw FASTQ files, QIIME2 artifacts, PICRUSt2 intermediate outputs, source sample identifiers, and individual-level metadata are not included.

## Data

[`data/processed/`](data/processed/) contains the curated public CSV datasets. The sample labels (`Ctrl1`-`Ctrl4`, `RB1`-`RB4`, and `FRB1`-`FRB4`) are anonymized within-study labels. File definitions and limitations are in [`data/processed/README.md`](data/processed/README.md).

## Methods and outputs

The sequencing service, QIIME2 reanalysis, PICRUSt2 inference, transformation, statistical analysis, and figure definitions are documented in [`docs/main_figures_methods_and_legends.md`](docs/main_figures_methods_and_legends.md).

- Figure 4: group-mean resolved-taxon composition and four targeted relative-abundance panels.
- Figure 5: five low-P predicted MetaCyc pathways and FRB taxon contributions to chorismate metabolism and L-tryptophan biosynthesis.

PICRUSt2 results represent predicted microbial functional potential, not direct measurements of metabolites, pathway flux, enzyme activity, or host responses.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Reproduce from private computational inputs

The public CSV files enable inspection of the displayed values. Full reruns require the locally retained sequencing and QIIME2/PICRUSt2 inputs.

```bash
python scripts/run_analysis.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --out-dir <analysis-root>/ricebran_results

PYTHONPATH=src python3 scripts/build_annotations.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results

PYTHONPATH=src python3 scripts/rank_primary_pathway_contributors.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results

PYTHONPATH=src python3 scripts/build_main_figures.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results \
  --figures-dir figures
```

The figure command writes `figure4_16s_community_structure.pdf`, `figure5_predicted_metagenome.pdf`, and the two-page editable vector PDF `frb_primary_figures_4_5.pdf`.

To regenerate the curated public CSV files from the local inputs:

```bash
PYTHONPATH=src python3 scripts/export_public_processed_data.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results
```

## QIIME2 workflow

[`docs/qiime2.md`](docs/qiime2.md) describes manifest generation, DADA2 denoising, taxonomy assignment, diversity artifacts, and exports required for PICRUSt2. [`docs/qiime2_checklist.md`](docs/qiime2_checklist.md) provides QC checks for local reruns.

## Release and citation

- [`docs/data_availability.md`](docs/data_availability.md): public-data boundary and identifiers.
- [`docs/release_checklist.md`](docs/release_checklist.md): publication-release checks.
- [`CITATION.cff`](CITATION.cff): citation metadata.

Use a versioned GitHub Release or its Zenodo archive when citing this software snapshot.
