# FRB 16S rRNA 予測メタゲノム解析

このリポジトリは、対照群（Ctrl）、米糠群（RB）、発酵米糠群（FRB）の糞便16S rRNA解析およびPICRUSt2による予測メタゲノム解析を再現するための公開コードです。公開範囲はFRBの16S/PICRUSt2解析と、主となる菌叢組成・予測機能出力に限定します。

**関連研究:** *Rice bran fermented with fish-processing-associated microorganisms enhances intestinal mucus formation through modulation of the gut microbiota*. 本リポジトリが扱うのは、この研究のうちFRBの16S rRNA／PICRUSt2解析部分のみです。

## 公開内容

- QIIME2/PICRUSt2の解析コードと設定。
- 主出力に用いた匿名化済み処理CSV。
- Methods、図の定義、データ公開方針。
- GitHub Releaseに添付した2主図の編集可能なベクターPDF。

raw FASTQ、QIIME2 artifact、PICRUSt2中間生成物、元sample ID、個体対応metadataは含めません。

## 公開データ

[`data/processed/`](data/processed/) に主出力用の処理CSVを収録しています。`Ctrl1`-`Ctrl4`、`RB1`-`RB4`、`FRB1`-`FRB4` は群内の匿名化ラベルです。列定義と制限は [`data/processed/README.md`](data/processed/README.md) を参照してください。

## Methodsと主出力

シーケンスサービス、QIIME2再解析、PICRUSt2推定、変換、統計、図の定義は [`docs/main_figures_methods_and_legends.md`](docs/main_figures_methods_and_legends.md) に記載しています。

- Figure 4: resolved taxonの群平均組成と4分類群の相対存在量。
- Figure 5: 未補正Kruskal-Wallis P値が低い5つの予測MetaCyc pathwayと、FRB群におけるchorismate metabolismおよびL-tryptophan biosynthesisへの分類群寄与。

PICRUSt2は微生物機能ポテンシャルの予測であり、代謝物量、フラックス、酵素活性、宿主応答の直接測定ではありません。

## 環境構築

```bash
python -m pip install -e ".[dev]"
```

## 非公開の計算入力から再実行する場合

公開CSVでは主出力の値を確認できます。全工程の再実行には、研究室で管理するシーケンスデータおよびQIIME2/PICRUSt2入力が必要です。

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

図の出力は `figure4_16s_community_structure.pdf`、`figure5_predicted_metagenome.pdf`、および編集可能な2ページPDF `frb_primary_figures_4_5.pdf` です。

公開CSVは次で再生成できます。

```bash
PYTHONPATH=src python3 scripts/export_public_processed_data.py \
  --config config/frb.toml \
  --base-dir <analysis-root> \
  --results-dir <analysis-root>/ricebran_results
```

## QIIME2と公開準備

- [`docs/qiime2.md`](docs/qiime2.md): manifest、DADA2、taxonomy、PICRUSt2出力の手順。
- [`docs/qiime2_checklist.md`](docs/qiime2_checklist.md): ローカル再実行時のQC。
- [`docs/data_availability.md`](docs/data_availability.md): 公開データの範囲と識別子。
- [`docs/release_checklist.md`](docs/release_checklist.md): 公開リリース前の確認項目。
- [`CITATION.cff`](CITATION.cff): 引用情報。
- Zenodo concept DOI: [`10.5281/zenodo.22227745`](https://doi.org/10.5281/zenodo.22227745)。
