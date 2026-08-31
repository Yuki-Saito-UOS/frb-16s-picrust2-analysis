# QIIME2 and PICRUSt2 workflow

This guide describes the local FRB workflow from paired-end FASTQ files to the QIIME2 and PICRUSt2 outputs required by this repository. Review [`qiime2_checklist.md`](qiime2_checklist.md) before fixing parameters in `config/frb.toml`.

## Build the manifest

```bash
python scripts/build_manifest.py \
  --config config/frb.toml \
  --raw-dir <analysis-root>/ricebran_raw \
  --out-dir <analysis-root>/ricebran_QIIME
```

## Start QIIME2

```bash
docker run -it --rm \
  -v <analysis-root>:/work \
  quay.io/qiime2/amplicon:2024.10
```

Import paired reads and create a quality summary.

```bash
qiime tools import \
  --type 'SampleData[PairedEndSequencesWithQuality]' \
  --input-path /work/ricebran_QIIME/manifest.tsv \
  --output-path /work/ricebran_QIIME/demux.qza \
  --input-format PairedEndFastqManifestPhred33V2

qiime demux summarize \
  --i-data /work/ricebran_QIIME/demux.qza \
  --o-visualization /work/ricebran_QIIME/demux.qzv
```

Inspect `demux.qzv` before using the DADA2 parameters fixed in `config/frb.toml`.

```bash
qiime dada2 denoise-paired \
  --i-demultiplexed-seqs /work/ricebran_QIIME/demux.qza \
  --p-trim-left-f 0 \
  --p-trim-left-r 0 \
  --p-trunc-len-f 290 \
  --p-trunc-len-r 290 \
  --p-n-threads 4 \
  --o-table /work/ricebran_QIIME/table.qza \
  --o-representative-sequences /work/ricebran_QIIME/rep-seqs.qza \
  --o-denoising-stats /work/ricebran_QIIME/stats.qza
```

Create the standard quality-control visualizations.

```bash
qiime feature-table summarize \
  --i-table /work/ricebran_QIIME/table.qza \
  --o-visualization /work/ricebran_QIIME/table.qzv \
  --m-sample-metadata-file /work/ricebran_QIIME/metadata.tsv

qiime feature-table tabulate-seqs \
  --i-data /work/ricebran_QIIME/rep-seqs.qza \
  --o-visualization /work/ricebran_QIIME/rep-seqs.qzv

qiime metadata tabulate \
  --m-input-file /work/ricebran_QIIME/stats.qza \
  --o-visualization /work/ricebran_QIIME/stats.qzv
```

Apply feature filtering only when it was selected during quality control.

```bash
qiime feature-table filter-features \
  --i-table /work/ricebran_QIIME/table.qza \
  --p-min-frequency 10 \
  --p-min-samples 2 \
  --o-filtered-table /work/ricebran_QIIME/table-filtered.qza
```

## Assign taxonomy

Use a SILVA 138 Naive Bayes classifier compatible with the QIIME2 environment. A locally retained classifier can be mounted read-only.

```bash
docker run -it --rm \
  --platform linux/amd64 \
  -v <analysis-root>:/work \
  -v <classifier-dir>:/classifiers:ro \
  quay.io/qiime2/amplicon:2024.10

qiime feature-classifier classify-sklearn \
  --i-classifier /classifiers/silva-138-99-nb-classifier.qza \
  --i-reads /work/ricebran_QIIME/rep-seqs.qza \
  --o-classification /work/ricebran_QIIME/taxonomy.qza \
  --p-n-jobs 1

qiime metadata tabulate \
  --m-input-file /work/ricebran_QIIME/taxonomy.qza \
  --o-visualization /work/ricebran_QIIME/taxonomy.qzv
```

## Build diversity artifacts

```bash
qiime phylogeny align-to-tree-mafft-fasttree \
  --i-sequences /work/ricebran_QIIME/rep-seqs.qza \
  --o-alignment /work/ricebran_QIIME/aligned-rep-seqs.qza \
  --o-masked-alignment /work/ricebran_QIIME/masked-aligned-rep-seqs.qza \
  --o-tree /work/ricebran_QIIME/unrooted-tree.qza \
  --o-rooted-tree /work/ricebran_QIIME/rooted-tree.qza

qiime diversity core-metrics-phylogenetic \
  --i-phylogeny /work/ricebran_QIIME/rooted-tree.qza \
  --i-table /work/ricebran_QIIME/table.qza \
  --p-sampling-depth 2700 \
  --m-metadata-file /work/ricebran_QIIME/metadata.tsv \
  --output-dir /work/ricebran_QIIME/core-metrics-results
```

The sampling depth must be supported by `alpha-rarefaction.qzv` and the final study record.

## Export genus and PICRUSt2 inputs

```bash
qiime taxa collapse \
  --i-table /work/ricebran_QIIME/table.qza \
  --i-taxonomy /work/ricebran_QIIME/taxonomy.qza \
  --p-level 6 \
  --o-collapsed-table /work/ricebran_QIIME/table-genus.qza

qiime tools export \
  --input-path /work/ricebran_QIIME/table-genus.qza \
  --output-path /work/ricebran_QIIME/table_genus_export

biom convert \
  -i /work/ricebran_QIIME/table_genus_export/feature-table.biom \
  -o /work/ricebran_QIIME/table-genus.tsv \
  --to-tsv

qiime tools export \
  --input-path /work/ricebran_QIIME/rep-seqs.qza \
  --output-path /work/ricebran_QIIME/exported-rep-seqs

qiime tools export \
  --input-path /work/ricebran_QIIME/table.qza \
  --output-path /work/ricebran_QIIME/exported-table
```

Run PICRUSt2 with stratified output.

```bash
docker run -it --rm \
  -v <analysis-root>:/work \
  quay.io/biocontainers/picrust2:2.5.1--pyhdfd78af_0 \
  picrust2_pipeline.py \
  -s /work/ricebran_QIIME/exported-rep-seqs/dna-sequences.fasta \
  -i /work/ricebran_QIIME/exported-table/feature-table.biom \
  -o /work/ricebran_QIIME/picrust2_out \
  -p 4 \
  --stratified
```

## Verify inputs and run the Python workflow

```bash
python scripts/run_analysis.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --out-dir results/frb \
  --check-inputs

python scripts/run_analysis.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --out-dir results/frb
```

Required local outputs include `table-genus.tsv`, `exported-taxonomy/taxonomy.tsv`, `exported-rep-seqs/dna-sequences.fasta`, `path_abun_unstrat.tsv.gz`, and `path_abun_contrib.tsv.gz`.
