# raw FASTQ から QIIME2 を実行する手順

この手順は、`scripts/build_manifest.py` で paired-end 用の manifest を作成済みであることを前提にしています。

最終解析に進む前に `docs/qiime2_checklist.md` を確認します。確認後に採用した数値は、対応する `config/*.toml` に固定します。

## Manifest を作成する

```bash
python scripts/build_manifest.py \
  --config config/frb.toml \
  --raw-dir <analysis-root>/ricebran_raw \
  --out-dir <analysis-root>/ricebran_QIIME
```

FMT 側:

```bash
python scripts/build_manifest.py \
  --config config/frb.toml \
  --raw-dir <analysis-root>/ricebran_FMT_raw \
  --out-dir <analysis-root>/ricebran_FMT_QIIME
```

`ricebran_FMT_raw` の FASTQ ファイル名では `risebranFMT` という表記が使われています。サンプル照合を再現できるよう、config でも同じ表記を使います。

## Docker で QIIME2 を起動する

```bash
docker run -it --rm \
  -v <analysis-root>:/work \
  quay.io/qiime2/amplicon:2024.10
```

コンテナ内で paired reads を import します。

```bash
qiime tools import \
  --type 'SampleData[PairedEndSequencesWithQuality]' \
  --input-path /work/ricebran_QIIME/manifest.tsv \
  --output-path /work/ricebran_QIIME/demux.qza \
  --input-format PairedEndFastqManifestPhred33V2
```

read quality を確認するため、demux summary を作成します。

```bash
qiime demux summarize \
  --i-data /work/ricebran_QIIME/demux.qza \
  --o-visualization /work/ricebran_QIIME/demux.qzv
```

`demux.qzv` を確認して、DADA2 の `trim_left` と `trunc_len` を決めます。採用値は `config/*.toml` に固定します。

DADA2 の実行例です。`demux.qzv` を確認した後、config の `[qiime2.dada2]` に固定した採用値を使います。

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

上の値は config の以下に対応します。

- `config -> [qiime2.dada2].trim_left_f`
- `config -> [qiime2.dada2].trim_left_r`
- `config -> [qiime2.dada2].trunc_len_f`
- `config -> [qiime2.dada2].trunc_len_r`
- `config -> [qiime2.dada2].n_threads`

feature table、representative sequence、DADA2 stats を可視化します。

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

feature filtering を使う場合は、採用値を `[qiime2.feature_filter]` に記録します。下流で filtered table を使う場合は、以降の `table.qza` を `table-filtered.qza` に置き換えます。

```bash
qiime feature-table filter-features \
  --i-table /work/ricebran_QIIME/table.qza \
  --p-min-frequency 10 \
  --p-min-samples 2 \
  --o-filtered-table /work/ricebran_QIIME/table-filtered.qza
```

## Taxonomy annotation

QIIME2 2024.10 の Docker image では、scikit-learn 1.4.2 用に作成された classifier を使います。既存の classifier がローカルにある場合は、Docker に read-only mount して使います。例:

```bash
docker run -it --rm \
  --platform linux/amd64 \
  -v <analysis-root>:/work \
  -v <classifier-dir>:/classifiers:ro \
  quay.io/qiime2/amplicon:2024.10
```

この場合、classifier のパスはコンテナ内で `/classifiers/silva-138-99-nb-classifier.qza` です。

手元にない場合は、QIIME2 data bucket から QIIME2 2024.10 互換の SILVA classifier を取得します。

```bash
curl -L -o /work/ricebran_QIIME/silva-138-99-nb-classifier.qza \
  https://data.qiime2.org/classifiers/sklearn-1.4.2/silva/silva-138-99-nb-classifier.qza
```

2026-07-08 時点で QIIME2 data bucket にある SILVA 138 / sklearn 1.4.2 の主な classifier は以下です。

- `silva-138-99-nb-classifier.qza`: 標準 classifier。既存解析との比較を優先する場合はこちらを使う。
- `silva-138-99-nb-diverse-weighted-classifier.qza`: diverse-weighted 版。標準版より新しいが、別 classifier になるため過去結果との比較時は明記する。
- `silva-138-99-nb-human-stool-weighted-classifier.qza`: human stool weighted 版。今回の rice bran / fermented rice bran には通常使わない。

taxonomy を付与します。既存 classifier を mount した場合:

```bash
qiime feature-classifier classify-sklearn \
  --i-classifier /classifiers/silva-138-99-nb-classifier.qza \
  --i-reads /work/ricebran_QIIME/rep-seqs.qza \
  --o-classification /work/ricebran_QIIME/taxonomy.qza \
  --p-n-jobs 1

qiime metadata tabulate \
  --m-input-file /work/ricebran_QIIME/taxonomy.qza \
  --o-visualization /work/ricebran_QIIME/taxonomy.qzv

qiime taxa barplot \
  --i-table /work/ricebran_QIIME/table.qza \
  --i-taxonomy /work/ricebran_QIIME/taxonomy.qza \
  --m-metadata-file /work/ricebran_QIIME/metadata.tsv \
  --o-visualization /work/ricebran_QIIME/taxa-barplot.qzv
```

## 系統樹と diversity

系統樹を作成します。

```bash
qiime phylogeny align-to-tree-mafft-fasttree \
  --i-sequences /work/ricebran_QIIME/rep-seqs.qza \
  --o-alignment /work/ricebran_QIIME/aligned-rep-seqs.qza \
  --o-masked-alignment /work/ricebran_QIIME/masked-aligned-rep-seqs.qza \
  --o-tree /work/ricebran_QIIME/unrooted-tree.qza \
  --o-rooted-tree /work/ricebran_QIIME/rooted-tree.qza
```

rarefaction を使う場合は、先に `table.qzv` や `alpha-rarefaction.qzv` を確認し、その後 `[qiime2.rarefaction]` の `sampling_depth` のコメントを外して採用値を固定します。以下の `2500` は例です。

```bash
qiime diversity core-metrics-phylogenetic \
  --i-phylogeny /work/ricebran_QIIME/rooted-tree.qza \
  --i-table /work/ricebran_QIIME/table.qza \
  --p-sampling-depth 2500 \
  --m-metadata-file /work/ricebran_QIIME/metadata.tsv \
  --output-dir /work/ricebran_QIIME/core-metrics-results

qiime diversity beta-group-significance \
  --i-distance-matrix /work/ricebran_QIIME/core-metrics-results/bray_curtis_distance_matrix.qza \
  --m-metadata-file /work/ricebran_QIIME/metadata.tsv \
  --m-metadata-column group \
  --o-visualization /work/ricebran_QIIME/core-metrics-results/bray-curtis-group-significance.qzv \
  --p-pairwise

qiime diversity alpha-group-significance \
  --i-alpha-diversity /work/ricebran_QIIME/core-metrics-results/shannon_vector.qza \
  --m-metadata-file /work/ricebran_QIIME/metadata.tsv \
  --o-visualization /work/ricebran_QIIME/shannon-group-significance.qzv
```

## Genus table を作成する

Python 解析で使う genus table と taxonomy table を export します。

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
  --input-path /work/ricebran_QIIME/taxonomy.qza \
  --output-path /work/ricebran_QIIME/exported-taxonomy
```

## PICRUSt2 用に export する

QIIME2 コンテナ内で rep-seqs と table を export します。

```bash
qiime tools export \
  --input-path /work/ricebran_QIIME/rep-seqs.qza \
  --output-path /work/ricebran_QIIME/exported-rep-seqs

qiime tools export \
  --input-path /work/ricebran_QIIME/table.qza \
  --output-path /work/ricebran_QIIME/exported-table

biom convert \
  -i /work/ricebran_QIIME/exported-table/feature-table.biom \
  -o /work/ricebran_QIIME/table.tsv \
  --to-tsv
```

QIIME2 コンテナを抜けてから、PICRUSt2 コンテナを実行します。

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

PICRUSt2 由来の解釈で NSTI filtering を使う場合は、採用した閾値を `[picrust2].max_nsti` に記録します。

## 入力ファイルの存在確認

Python 側から、genus table と PICRUSt2 の想定出力が存在するか確認できます。

```bash
python scripts/run_analysis.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --out-dir results/frb \
  --check-inputs
```

主に確認するファイル:

```text
ricebran_QIIME/
  metadata.tsv
  manifest.tsv
  demux.qza
  demux.qzv
  table.qza
  table.qzv
  rep-seqs.qza
  rep-seqs.qzv
  stats.qza
  stats.qzv
  taxonomy.qza
  taxonomy.qzv
  taxa-barplot.qzv
  rooted-tree.qza
  core-metrics-results/
  table-genus.qza
  table-genus.tsv
  exported-taxonomy/taxonomy.tsv
  exported-rep-seqs/dna-sequences.fasta
  exported-table/feature-table.biom
  picrust2_out/
    EC_metagenome_out/pred_metagenome_contrib.tsv.gz
    KO_metagenome_out/pred_metagenome_contrib.tsv.gz
    pathways_out/path_abun_unstrat.tsv.gz
    pathways_out/path_abun_contrib.tsv.gz
```

QIIME2 / PICRUSt2 の出力が揃ったら、Python 側の解析を実行します。

```bash
python scripts/run_analysis.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --out-dir results/frb
```
