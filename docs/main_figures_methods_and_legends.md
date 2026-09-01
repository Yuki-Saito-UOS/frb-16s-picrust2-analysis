# Methods and figure definitions

This document defines the public FRB 16S rRNA and predicted-metagenome workflow and its two primary figure outputs.

## Methods

### 16S rRNA sequence processing and community composition analysis

Fresh fecal samples were stored at -80 degrees C until analysis. DNA extraction, amplification, and V3-V4 16S rRNA gene sequencing were performed by TechnoSuruga Laboratory Co., Ltd. (Shizuoka, Japan). The V3-V4 region was amplified with Pro341F and Pro805R primers, dual-indexed libraries with 8-bp barcodes were prepared, and paired-end sequencing was performed with a MiSeq  system using the MiSeq  25M Reagent Kit v3 (600 cycles; Illumina). The service workflow removed primers with Cutadapt version 1.1.8, merged read pairs with fastq-join version 1.3.1, retained joined reads with at least 99% of bases at Q20 or higher, and removed chimeras with USEARCH version 6.1.544_i86.

The public computational workflow starts from the delivered paired-end FASTQ files and analyzes control, rice bran (RB), and fermented rice bran (FRB) groups, with four mice per group. Reads were imported into QIIME 2 using manifest files generated from the analysis configuration. Denoising used DADA2 with `trim_left_f = 0`, `trim_left_r = 0`, `trunc_len_f = 290`, `trunc_len_r = 290`, and four threads. Taxonomy was assigned with a SILVA 138 Naive Bayes classifier compatible with the QIIME 2 environment, and the feature table was collapsed at genus level. Representative sequences and feature tables were exported for functional prediction. Figure 4 uses the resulting genus-level relative-abundance table across all panels.

For the community-composition panel, genus-level abundances were converted to within-sample relative abundances and summarized as group means. The pre-specified taxon panels show per-sample relative abundances for Lactobacillaceae, A2, Lachnospiraceae_NK4A136_group, and Lachnospiraceae_UCG-006. Omnibus three-group differences in the displayed taxon panels were assessed using the Kruskal-Wallis test; asterisks denote unadjusted `p < 0.05`. These four taxon tests are targeted displays and should not be interpreted as an FDR-controlled discovery screen.

### Predicted metagenome analysis

Predicted microbial functions were inferred with PICRUSt2 version 2.5.1 from ASV representative sequences and feature abundances, with stratified output enabled. The unstratified MetaCyc pathway table (`path_abun_unstrat.tsv.gz`) was converted to within-sample relative abundance, multiplied by 1,000,000, and transformed with `log1p` before pathway-level statistical analysis. Differences among Ctrl, RB, and FRB were assessed with the Kruskal-Wallis test. For the primary heatmap, pathways were ranked by unadjusted Kruskal-Wallis P value and the five lowest-P pathways were displayed: the superpathways of chorismate metabolism, L-tryptophan biosynthesis, (Kdo)2-lipid A biosynthesis, L-threonine metabolism, and lipopolysaccharide biosynthesis. Pathway names and reaction metadata were annotated using PICRUSt2 MetaCyc pathway information and additional public-database annotation tables. The heatmap displays row-wise z-scores across samples and is a visualization of predicted pathway abundance rather than a direct functional measurement.

Stratified PICRUSt2 pathway contributions (`path_abun_contrib.tsv.gz`) were used to calculate resolved-taxon contributions. ASVs absent from a sample were assigned a contribution of zero when calculating group means. The relative contribution bars display the complete FRB-group pathway contribution for the chorismate-metabolism and L-tryptophan-biosynthesis superpathways; lower-ranked contributors are combined into `Other`. PICRUSt2 analyses represent predicted microbial functional potential and do not directly measure metabolite concentrations, pathway flux, enzyme activity, or host receptor activation.

## Figure legends

### Figure 4. Fermented rice bran alters the intestinal microbial community composition.

Group-mean relative abundance of the 20 most abundant resolved taxa; remaining taxa are grouped as `Other`. Lower panels show per-sample relative abundances of Lactobacillaceae, A2, Lachnospiraceae_NK4A136_group, and Lachnospiraceae_UCG-006. Points represent individual samples. Horizontal bars and asterisks indicate unadjusted Kruskal-Wallis `p < 0.05` across the three groups.

Output: `figures/figure4_16s_community_structure.pdf`.

### Figure 5. Predicted microbial functional profile and taxon contributions in the fermented rice bran group.

Row-wise z-scored abundance of the five predicted MetaCyc pathways with the lowest unadjusted Kruskal-Wallis P values across individual samples. Vertical separators distinguish control, RB, and FRB samples. Relative resolved-taxon contributions to the predicted superpathways of chorismate metabolism and L-tryptophan biosynthesis in the FRB group were calculated from stratified PICRUSt2 output. The denominator includes the complete pathway contribution, and lower-ranked taxa are retained in `Other`.

Output: `figures/figure5_predicted_metagenome.pdf`.

The two figure pages are also delivered together as the editable vector PDF `figures/frb_primary_figures_4_5.pdf`.

## Reproduction command

```bash
PYTHONPATH=src python3 scripts/build_annotations.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir results/frb

PYTHONPATH=src python3 scripts/rank_primary_pathway_contributors.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir results/frb

PYTHONPATH=src python3 scripts/build_main_figures.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir results/frb \
  --figures-dir figures
```
