from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Dada2Config:
    trim_left_f: int = 0
    trim_left_r: int = 0
    trunc_len_f: int = 290
    trunc_len_r: int = 290
    n_threads: int = 4


@dataclass(frozen=True)
class FeatureFilterConfig:
    min_frequency: int = 10
    min_samples: int = 2


@dataclass(frozen=True)
class RarefactionConfig:
    sampling_depth: int | None = None


@dataclass(frozen=True)
class Picrust2Config:
    max_nsti: float | None = None


@dataclass(frozen=True)
class Qiime2Config:
    dada2: Dada2Config
    feature_filter: FeatureFilterConfig
    rarefaction: RarefactionConfig


@dataclass(frozen=True)
class AnalysisConfig:
    target: str
    groups: dict[str, list[str]]
    raw_dirname: str = "ricebran_raw"
    qiime_dirname: str = "ricebran_QIIME"
    results_dirname: str = "ricebran_results"
    picrust2_dirname: str = "picrust2_out"
    docker_raw_dir: str | None = None
    p_value: float = 0.05
    effect: float = 0.20
    top_n: int = 30
    qiime2: Qiime2Config = field(
        default_factory=lambda: Qiime2Config(
            dada2=Dada2Config(),
            feature_filter=FeatureFilterConfig(),
            rarefaction=RarefactionConfig(),
        )
    )
    picrust2: Picrust2Config = field(default_factory=Picrust2Config)


@dataclass(frozen=True)
class ProjectPaths:
    base_dir: Path
    out_dir: Path
    qiime_dirname: str = "ricebran_QIIME"
    picrust2_dirname: str = "picrust2_out"
    results_dirname: str = "ricebran_results"

    @property
    def configured_qiime_dir(self) -> Path:
        return self.base_dir / self.qiime_dirname

    @property
    def fallback_qiime_dir(self) -> Path:
        return self.base_dir / "data" / "qiime"

    @property
    def qiime_dir(self) -> Path:
        return self.configured_qiime_dir if self.configured_qiime_dir.exists() else self.fallback_qiime_dir

    @property
    def configured_picrust2_dir(self) -> Path:
        return self.configured_qiime_dir / self.picrust2_dirname

    @property
    def configured_results_dir(self) -> Path:
        return self.base_dir / self.results_dirname

    @property
    def picrust2_dir(self) -> Path:
        return self.qiime_dir / self.picrust2_dirname

    @property
    def genus_table(self) -> Path:
        return self.qiime_dir / "table-genus.tsv"

    @property
    def configured_genus_table(self) -> Path:
        return self.configured_qiime_dir / "table-genus.tsv"

    def _picrust2_path(self, *parts: str, configured: bool = False) -> Path:
        root = self.configured_picrust2_dir if configured else self.picrust2_dir
        return root.joinpath(*parts)

    @property
    def pathway_unstrat(self) -> Path:
        return self._picrust2_path("pathways_out", "path_abun_unstrat.tsv.gz")

    @property
    def pathway_contrib(self) -> Path:
        return self._picrust2_path("pathways_out", "path_abun_contrib.tsv.gz")

    @property
    def ec_contrib(self) -> Path:
        return self._picrust2_path("EC_metagenome_out", "pred_metagenome_contrib.tsv.gz")

    @property
    def ko_contrib(self) -> Path:
        return self._picrust2_path("KO_metagenome_out", "pred_metagenome_contrib.tsv.gz")

    @property
    def picrust2_expected_paths(self) -> dict[str, Path]:
        return {
            "picrust2": self.configured_picrust2_dir,
            "pathways_out": self.configured_picrust2_dir / "pathways_out",
            "ec_out": self.configured_picrust2_dir / "EC_metagenome_out",
            "ko_out": self.configured_picrust2_dir / "KO_metagenome_out",
            "pathway_unstrat": self._picrust2_path("pathways_out", "path_abun_unstrat.tsv.gz", configured=True),
            "pathway_contrib": self._picrust2_path("pathways_out", "path_abun_contrib.tsv.gz", configured=True),
            "ec_contrib": self._picrust2_path(
                "EC_metagenome_out",
                "pred_metagenome_contrib.tsv.gz",
                configured=True,
            ),
            "ko_contrib": self._picrust2_path(
                "KO_metagenome_out",
                "pred_metagenome_contrib.tsv.gz",
                configured=True,
            ),
        }

    def existing_picrust2_paths(self) -> dict[str, bool]:
        return {name: path.exists() for name, path in self.picrust2_expected_paths.items()}


def load_config(path: Path) -> AnalysisConfig:
    data = tomllib.loads(path.read_text())
    project = data.get("project", {})
    thresholds = data.get("thresholds", {})
    qiime2 = data.get("qiime2", {})
    dada2 = qiime2.get("dada2", {})
    feature_filter = qiime2.get("feature_filter", {})
    rarefaction = qiime2.get("rarefaction", {})
    picrust2 = data.get("picrust2", {})
    return AnalysisConfig(
        target=project.get("target", "ricebran"),
        groups={k: list(v) for k, v in data.get("groups", {}).items()},
        raw_dirname=project.get("raw_dirname", "ricebran_raw"),
        qiime_dirname=project.get("qiime_dirname", "ricebran_QIIME"),
        results_dirname=project.get("results_dirname", "ricebran_results"),
        picrust2_dirname=project.get("picrust2_dirname", "picrust2_out"),
        docker_raw_dir=project.get("docker_raw_dir"),
        p_value=float(thresholds.get("p_value", 0.05)),
        effect=float(thresholds.get("effect", 0.20)),
        top_n=int(thresholds.get("top_n", 30)),
        qiime2=Qiime2Config(
            dada2=Dada2Config(
                trim_left_f=int(dada2.get("trim_left_f", 0)),
                trim_left_r=int(dada2.get("trim_left_r", 0)),
                trunc_len_f=int(dada2.get("trunc_len_f", 290)),
                trunc_len_r=int(dada2.get("trunc_len_r", 290)),
                n_threads=int(dada2.get("n_threads", 4)),
            ),
            feature_filter=FeatureFilterConfig(
                min_frequency=int(feature_filter.get("min_frequency", 10)),
                min_samples=int(feature_filter.get("min_samples", 2)),
            ),
            rarefaction=RarefactionConfig(
                sampling_depth=rarefaction.get("sampling_depth"),
            ),
        ),
        picrust2=Picrust2Config(
            max_nsti=picrust2.get("max_nsti"),
        ),
    )
