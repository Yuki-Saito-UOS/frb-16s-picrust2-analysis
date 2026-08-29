# Public release checklist

Use this checklist before making a public GitHub release.

## Repository metadata

- [ ] `README.md` explains the workflow, required inputs, and expected outputs.
- [ ] `README.ja.md` is consistent with the English README.
- [ ] `LICENSE` is present and appropriate for public code reuse.
- [ ] `CITATION.cff` has the correct author list, release version, release date, and archived DOI.
- [ ] `docs/data_availability.md` contains final accession numbers and DOI links.

## Reproducibility

- [ ] `python -m pip install -e .[dev]` succeeds in a clean Python environment.
- [ ] `pytest` passes.
- [ ] `python scripts/run_analysis.py --config config/frb.toml --base-dir <analysis-root> --out-dir results/frb --check-inputs` shows all required inputs as present.
- [ ] `docs/qiime2_checklist.md` or a dated run note records the final DADA2, filtering, rarefaction, taxonomy, and PICRUSt2 decisions.
- [ ] `scripts/build_main_figures.py` reproduces `figure4_16s_community_structure.pdf`, `figure5_predicted_metagenome.pdf`, and the combined editable vector PDF `frb_primary_figures_4_5.pdf` from the final QIIME2 and PICRUSt2 inputs.

## Public disclosure

- [ ] Raw FASTQ, QIIME2 artifacts, PICRUSt2 outputs, non-curated generated results, and generated figures are not committed outside an approved release asset.
- [ ] The curated files in `data/processed/` contain only the documented public sample labels and primary-figure values; source sample identifiers and individual-level metadata are absent.
- [ ] Local absolute paths have been replaced with `<analysis-root>` or another non-identifying placeholder.
- [ ] No unpublished collaborator-only results outside the declared public scope are included.
- [ ] All table and figure labels match the approved study terminology.

## Statistical and interpretation checks

- [ ] Multiple-testing correction is reported for each output table.
- [ ] Documentation distinguishes PICRUSt2 predictions from experimentally validated functional changes.
- [ ] Effect sizes are interpreted on the transformed abundance scale used by the scripts.
- [ ] Small sample size limitations are stated.
