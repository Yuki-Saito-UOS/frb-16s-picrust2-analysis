# Data Policy

このディレクトリには、公開可能な処理済みデータと配置ルールを置きます。

`processed/` には、論文の Figure 4・5 の再作図に必要な匿名化済み集計 CSV を収録します。
各ファイルの値は、公開対象のFRB解析で用いたQIIME2/PICRUSt2出力から生成されています。`sample_id` は群内の匿名化ラベルであり、個体IDではありません。

Git 管理しないもの:

- raw FASTQ
- QIIME2 artifacts (`*.qza`, `*.qzv`)
- PICRUSt2 outputs
- 公開対象の図に使用していない解析結果 TSV
- 図表ファイル

既存データを使う場合は `scripts/run_analysis.py --base-dir <analysis-root>` のように外部ディレクトリを指定してください。

公開CSVは次で生成します。

```bash
PYTHONPATH=src python3 scripts/export_public_processed_data.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results
```

論文公開時は、生 FASTQ の公開 accession、archived code DOI を `docs/data_availability.md` に記録します。
