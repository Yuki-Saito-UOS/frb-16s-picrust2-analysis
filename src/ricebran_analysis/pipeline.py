from __future__ import annotations

import os
from pathlib import Path
import shutil

from .config import AnalysisConfig, ProjectPaths
from .genus import analyze_genus
from .pathway import analyze_pathways


def _clear_extended_attrs(path: Path) -> None:
    if not hasattr(os, "listxattr") or not hasattr(os, "removexattr"):
        return
    try:
        for attr in os.listxattr(path):
            os.removexattr(path, attr)
    except OSError:
        pass


def _cleanup_sidecars(outputs: dict[str, Path]) -> None:
    for path in outputs.values():
        _clear_extended_attrs(path)
        (path.parent / f"._{path.name}").unlink(missing_ok=True)


def _mirror_outputs(outputs: dict[str, Path], mirror_dir: Path) -> dict[str, Path]:
    if not outputs:
        return {}

    mirror_dir.mkdir(parents=True, exist_ok=True)
    mirrored: dict[str, Path] = {}
    for name, path in outputs.items():
        mirror_path = mirror_dir / path.name
        if mirror_path.resolve() == path.resolve():
            continue
        shutil.copyfile(path, mirror_path)
        mirrored[f"{name}_external"] = mirror_path
    _cleanup_sidecars(mirrored)
    return mirrored


def run_pipeline(paths: ProjectPaths, config: AnalysisConfig) -> dict[str, Path]:
    paths.out_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    if paths.genus_table.exists():
        outputs.update(analyze_genus(paths.genus_table, paths.out_dir, config))

    if paths.pathway_unstrat.exists():
        outputs.update(analyze_pathways(paths.pathway_unstrat, paths.out_dir, config))

    _cleanup_sidecars(outputs)
    outputs.update(_mirror_outputs(outputs, paths.configured_results_dir))

    return outputs
