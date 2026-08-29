from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from ricebran_analysis.config import load_config
from ricebran_analysis.qiime_artifacts import read_alpha_diversity_qza, read_pcoa_qza


def test_frb_config_loads() -> None:
    config = load_config(Path("config/frb.toml"))

    assert config.target == "FRB"
    assert set(config.groups) == {"control", "ricebran", "Fermented_ricebran"}
    assert config.qiime2.dada2.trunc_len_f == 290


def test_reads_qiime2_alpha_diversity_and_pcoa_artifacts(tmp_path) -> None:
    alpha_path = tmp_path / "shannon.qza"
    with ZipFile(alpha_path, "w") as archive:
        archive.writestr("artifact/data/alpha-diversity.tsv", "\tshannon_entropy\nsample1\t1.2\nsample2\t2.3\n")
    alpha = read_alpha_diversity_qza(alpha_path)
    assert alpha.loc["sample1", "shannon_entropy"] == 1.2

    pcoa_path = tmp_path / "pcoa.qza"
    content = "\n".join(
        [
            "Eigvals\t2",
            "0.8\t0.2",
            "",
            "Proportion explained\t2",
            "0.8\t0.2",
            "",
            "Species\t0\t0",
            "",
            "Site\t2\t2",
            "sample1\t0.1\t-0.2",
            "sample2\t-0.1\t0.2",
        ]
    )
    with ZipFile(pcoa_path, "w") as archive:
        archive.writestr("artifact/data/ordination.txt", content)
    coordinates, explained = read_pcoa_qza(pcoa_path)
    assert coordinates.loc["sample2", "PC2"] == 0.2
    assert explained.loc["PC1"] == 0.8
