# Data Policy

This directory contains the public processed data and its storage policy.

`processed/` contains the anonymized summary CSV files required to reproduce Figures 4 and 5. Values are derived from the QIIME2 and PICRUSt2 outputs used for the public FRB analysis. `sample_id` is an anonymized within-study label, not an individual identifier.

The following files are not tracked by Git:

- raw FASTQ
- QIIME2 artifacts (`*.qza`, `*.qzv`)
- PICRUSt2 outputs
- Analysis-result TSV files not used for the public figures.
- Figure files.

For locally retained inputs, specify an external directory, for example `scripts/run_analysis.py --base-dir <analysis-root>`.

Generate the public CSV files with:

```bash
PYTHONPATH=src python3 scripts/export_public_processed_data.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results
```

Raw FASTQ files are not part of this public archive. Record the archived-code DOI in `docs/data_availability.md` after the Zenodo release.
