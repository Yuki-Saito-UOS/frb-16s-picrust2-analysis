# Public processed datasets

These CSV files are the curated, anonymized inputs required to inspect the values shown in the primary FRB Figures 4 and 5. `sample_id` values (`Ctrl1`–`Ctrl4`, `RB1`–`RB4`, and `FRB1`–`FRB4`) are public within-study labels only; they are not source sample identifiers.

| File | Contents |
| --- | --- |
| `sample_groups.csv` | Public sample labels and study group. |
| `genus_relative_abundance.csv` | Resolved-taxon relative abundance for all displayed-study samples. |
| `figure4_display_taxa.csv` | Long-format relative abundances for the four Figure 4 taxon panels. |
| `figure5_selected_pathway_abundance.csv` | PICRUSt2-predicted abundance for the five Figure 5 heatmap pathways. |
| `figure5_frb_taxon_contributions.csv` | FRB group-mean resolved-taxon contributions for the two Figure 5 contribution pathways. |

All functional values are PICRUSt2 predictions. They must not be interpreted as direct measurements of metabolites, pathway flux, enzyme activity, or host responses. For pathway-level statistics, the complete unstratified table is converted to within-sample relative abundance, multiplied by 1,000,000, and `log1p`-transformed before the Kruskal-Wallis ranking that selects the five Figure 5 pathways.

To recreate these files from the private computational inputs, run `scripts/export_public_processed_data.py`. Do not add raw reads, QIIME2 artifacts, PICRUSt2 intermediate files, or individual-level metadata to this directory.
