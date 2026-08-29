from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd

from .config import AnalysisConfig
from .io import sample_to_group


FASTQ_RE = re.compile(r"^(?P<sample>.+)_R(?P<read>[12])(?:_\d+)?\.(?:fastq|fq)(?:\.gz)?$")


@dataclass(frozen=True)
class FastqPair:
    sample: str
    forward: Path
    reverse: Path
    group: str | None


def _prefer_fastq(existing: Path | None, candidate: Path) -> Path:
    if existing is None:
        return candidate
    if candidate.suffix == ".gz" and existing.suffix != ".gz":
        return candidate
    return existing


def scan_paired_fastq(raw_dir: Path, groups: dict[str, list[str]]) -> list[FastqPair]:
    reads: dict[str, dict[str, Path]] = {}

    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name.startswith("._"):
            continue
        match = FASTQ_RE.match(path.name)
        if match is None:
            continue

        sample = match.group("sample")
        read = match.group("read")
        reads.setdefault(sample, {})
        reads[sample][read] = _prefer_fastq(reads[sample].get(read), path)

    pairs = []
    for sample, sample_reads in sorted(reads.items()):
        if "1" not in sample_reads or "2" not in sample_reads:
            continue
        pairs.append(
            FastqPair(
                sample=sample,
                forward=sample_reads["1"].resolve(),
                reverse=sample_reads["2"].resolve(),
                group=sample_to_group(sample, groups),
            )
        )
    return pairs


def write_qiime_manifest(raw_dir: Path, out_dir: Path, config: AnalysisConfig) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = scan_paired_fastq(raw_dir, config.groups)
    docker_raw_dir = config.docker_raw_dir.rstrip("/") if config.docker_raw_dir else None

    def manifest_path(path: Path) -> str:
        if docker_raw_dir is not None:
            return f"{docker_raw_dir}/{path.name}"
        return str(path)

    manifest = pd.DataFrame(
        [
            {
                "sample-id": pair.sample,
                "forward-absolute-filepath": manifest_path(pair.forward),
                "reverse-absolute-filepath": manifest_path(pair.reverse),
            }
            for pair in pairs
        ]
    )
    metadata = pd.DataFrame(
        [
            {
                "sample-id": pair.sample,
                "group": pair.group or "unknown",
            }
            for pair in pairs
        ]
    )

    manifest_path = out_dir / "manifest.tsv"
    metadata_path = out_dir / "metadata.tsv"
    manifest.to_csv(manifest_path, sep="\t", index=False)
    metadata.to_csv(metadata_path, sep="\t", index=False)

    return {"manifest": manifest_path, "metadata": metadata_path}
