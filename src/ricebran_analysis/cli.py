from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProjectPaths, load_config
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run rice bran microbiome analysis.")
    parser.add_argument("--config", type=Path, default=Path("config/frb.toml"))
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("results"))
    parser.add_argument("--check-inputs", action="store_true", help="Print expected input paths and exit.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    paths = ProjectPaths(
        base_dir=args.base_dir.expanduser().resolve(),
        out_dir=args.out_dir.resolve(),
        qiime_dirname=config.qiime_dirname,
        picrust2_dirname=config.picrust2_dirname,
        results_dirname=config.results_dirname,
    )

    if args.check_inputs:
        print("Expected input paths:")
        print(f"- qiime_dir: {'OK' if paths.configured_qiime_dir.exists() else 'MISSING'}  {paths.configured_qiime_dir}")
        print(
            f"- genus_table: {'OK' if paths.configured_genus_table.exists() else 'MISSING'}  "
            f"{paths.configured_genus_table}"
        )
        for name, path in paths.picrust2_expected_paths.items():
            print(f"- {name}: {'OK' if path.exists() else 'MISSING'}  {path}")
        return

    outputs = run_pipeline(paths, config)

    if not outputs:
        print("No expected input files were found. See data/README.md.")
        return

    print("Saved outputs:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
