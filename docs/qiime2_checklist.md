# QIIME2 / PICRUSt2 判断チェックリスト

raw FASTQ から QIIME2 / PICRUSt2 を実行するときに使うチェックリストです。確認後に採用した数値は `config/*.toml` に固定し、なぜその値を採用したかをこのファイル、または日付付きの実行メモに残します。

## 実行情報

- データセット:
- 使用した config:
- raw FASTQ ディレクトリ:
- QIIME2 出力ディレクトリ:
- 確認者:
- 日付:

## 1. Manifest / Metadata

- [ ] `manifest.tsv` に想定した全サンプルが含まれている。
- [ ] `metadata.tsv` で各サンプルが正しい group に割り当てられている。
- [ ] 意図して残す場合を除き、`unknown` group のサンプルがない。
- [ ] FASTQ ファイル名、sample ID、config のサンプル名の表記が一致している。

config に固定する項目:

- `config -> [groups]`
- `config -> [project.raw_dirname]`
- `config -> [project.qiime_dirname]`

メモ:

```text

```

## 2. Demux Quality

`demux.qzv` を作成して確認します。

- [ ] forward read の quality が、採用する truncation 位置まで十分に保たれている。
- [ ] reverse read の quality が、採用する truncation 位置まで十分に保たれている。
- [ ] truncation 後も paired-end join に必要な overlap が残る。
- [ ] read 数が極端に少ないサンプルを確認し、後続工程で注意する。

config に固定する項目:

- `config -> [qiime2.dada2].trim_left_f`
- `config -> [qiime2.dada2].trim_left_r`
- `config -> [qiime2.dada2].trunc_len_f`
- `config -> [qiime2.dada2].trunc_len_r`
- `config -> [qiime2.dada2].n_threads`

メモ:

```text

```

## 3. DADA2 Denoising Stats

`qiime dada2 denoise-paired` 実行後に `stats.qzv` を確認します。

- [ ] filtering 後に、多くのサンプルで十分な read 数が残っている。
- [ ] merging 後に、多くのサンプルで十分な read 数が残っている。
- [ ] non-chimeric read 数が極端に少ないサンプルを確認した。
- [ ] 除外するサンプルがある場合、理由と一緒に記録した。

判断:

- [ ] 全サンプルを残す。
- [ ] 下記サンプルを除外する。
- [ ] truncation / trim の値を変更して DADA2 を再実行する。

除外サンプル:

```text

```

メモ:

```text

```

## 4. Feature Table Filtering

下流解析の前に、低頻度 feature を除くか判断します。

- [ ] feature frequency の分布を確認した。
- [ ] `min_frequency` が、期待される生物学的シグナルを過剰に削らない値になっている。
- [ ] `min_samples` が、group レベルで見たい feature を残しつつ、ノイズらしい feature を除く値になっている。

config に固定する項目:

- `config -> [qiime2.feature_filter].min_frequency`
- `config -> [qiime2.feature_filter].min_samples`

メモ:

```text

```

## 5. Taxonomy

taxonomy assignment の出力を確認します。

- [ ] 使用した classifier / database のバージョンを記録した。
- [ ] phylum / family / genus レベルの taxonomy summary が妥当に見える。
- [ ] Unassigned や曖昧な分類が想定外に多くない。
- [ ] Python 解析用に genus レベルの `table-genus.tsv` を export した。

classifier / database:

```text

```

メモ:

```text

```

## 6. Rarefaction

rarefaction を解析に使う場合だけ確認します。

- [ ] `alpha-rarefaction.qzv` を確認した。
- [ ] 採用する sampling depth で、各 group に十分なサンプルが残る。
- [ ] 採用する sampling depth 付近で diversity curve が大きく不安定ではない。
- [ ] rarefaction を使わない場合、config の `sampling_depth` はコメントアウトしたままにする。

config に固定する項目:

- `config -> [qiime2.rarefaction].sampling_depth`

メモ:

```text

```

## 7. PICRUSt2

pathway table を使う前に、PICRUSt2 のログと出力を確認します。

- [ ] PICRUSt2 が failed sample なしで完了した。
- [ ] NSTI filtering を検討する場合、NSTI 分布を確認した。
- [ ] NSTI の除外閾値を使う場合、config に固定した。
- [ ] Python 解析用の `path_abun_unstrat.tsv.gz` が存在する。

config に固定する項目:

- `config -> [picrust2].max_nsti`

メモ:

```text

```

## 8. 最終 Python 解析

- [ ] `python scripts/run_analysis.py --config ...` が完了した。
- [ ] FRB の3群正本解析の出力が存在する。
  - `genus_stats_3group.tsv`
  - `TOP_genus_3group.tsv`
  - `pathway_stats_3group.tsv`
  - `TOP_pathways_3group.tsv`
- [ ] 設定された group の組み合わせごとに、2群補助解析の出力が存在する。
- [ ] 出力ディレクトリと使用した config を一緒に記録した。

メモ:

```text

```
