from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ricebran_analysis.config import load_config


DEFAULT_QIIME2_IMAGE = "quay.io/qiime2/amplicon@sha256:4038fd785bf4e76ddd6ec7a7f57abe94cdca6c5cd0a93d0924971a74eabd7cf2"
DEFAULT_DOCKER_PLATFORM = "linux/amd64"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DADA2 using adopted values from config.")
    parser.add_argument("--config", type=Path, required=True, help="Analysis config TOML.")
    parser.add_argument("--base-dir", type=Path, required=True, help="Directory mounted as /work in Docker.")
    parser.add_argument("--qiime2-image", default=DEFAULT_QIIME2_IMAGE)
    parser.add_argument("--docker-platform", default=DEFAULT_DOCKER_PLATFORM)
    parser.add_argument("--force", action="store_true", help="Overwrite existing DADA2 outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running Docker.")
    return parser


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def docker_run_command(base_dir: Path, image: str, qiime_args: list[str], docker_platform: str | None) -> list[str]:
    command = ["docker", "run", "--rm"]
    if docker_platform:
        command.extend(["--platform", docker_platform])
    command.extend(["-v", f"{base_dir}:/work", image, *qiime_args])
    return command


def run_command(command: list[str], dry_run: bool) -> None:
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, check=True)


def refuse_existing(paths: list[Path], force: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        print("Refusing to overwrite existing outputs. Use --force to overwrite:")
        for path in existing:
            print(f"- {path}")
        raise SystemExit(1)


def require_inputs(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.exists()]
    if missing:
        print("Missing required inputs:")
        for path in missing:
            print(f"- {path}")
        raise SystemExit(1)


def write_run_report(
    report_path: Path,
    *,
    config_path: Path,
    config_sha256: str,
    base_dir: Path,
    qiime_dir: Path,
    command_line: list[str],
    commands: list[list[str]],
    qiime2_image: str,
    docker_platform: str | None,
    dada2_values: dict[str, int],
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(repo_root),
        "command_line": command_line,
        "config": {
            "path": str(config_path),
            "sha256": config_sha256,
        },
        "paths": {
            "base_dir": str(base_dir),
            "qiime_dir": str(qiime_dir),
            "demux_qza": str(qiime_dir / "demux.qza"),
            "metadata": str(qiime_dir / "metadata.tsv"),
            "table_qza": str(qiime_dir / "table.qza"),
            "rep_seqs_qza": str(qiime_dir / "rep-seqs.qza"),
            "stats_qza": str(qiime_dir / "stats.qza"),
            "table_qzv": str(qiime_dir / "table.qzv"),
            "rep_seqs_qzv": str(qiime_dir / "rep-seqs.qzv"),
            "stats_qzv": str(qiime_dir / "stats.qzv"),
        },
        "docker": {
            "platform": docker_platform,
            "qiime2_image": qiime2_image,
            "commands": commands,
        },
        "dada2": dada2_values,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    args = build_parser().parse_args()
    config_path = args.config.expanduser().resolve()
    base_dir = args.base_dir.expanduser().resolve()
    config = load_config(config_path)
    qiime_dir = base_dir / config.qiime_dirname
    config_sha256 = sha256_file(config_path)
    dada2 = config.qiime2.dada2
    dada2_values = {
        "trim_left_f": dada2.trim_left_f,
        "trim_left_r": dada2.trim_left_r,
        "trunc_len_f": dada2.trunc_len_f,
        "trunc_len_r": dada2.trunc_len_r,
        "n_threads": dada2.n_threads,
    }

    inputs = [qiime_dir / "demux.qza", qiime_dir / "metadata.tsv"]
    outputs = [
        qiime_dir / "table.qza",
        qiime_dir / "rep-seqs.qza",
        qiime_dir / "stats.qza",
        qiime_dir / "table.qzv",
        qiime_dir / "rep-seqs.qzv",
        qiime_dir / "stats.qzv",
        qiime_dir / "dada2_run.json",
    ]

    print("Run DADA2")
    print(f"- config: {config_path}")
    print(f"- config_sha256: {config_sha256}")
    print(f"- base_dir: {base_dir}")
    print(f"- qiime_dir: {qiime_dir}")
    print(f"- qiime2_image: {args.qiime2_image}")
    print(f"- docker_platform: {args.docker_platform or '(default)'}")
    print("- dada2:")
    for name, value in dada2_values.items():
        print(f"  - {name}: {value}")

    require_inputs(inputs)
    refuse_existing(outputs, args.force or args.dry_run)

    qiime_prefix = f"/work/{config.qiime_dirname}"
    commands = [
        docker_run_command(
            base_dir,
            args.qiime2_image,
            [
                "qiime",
                "dada2",
                "denoise-paired",
                "--i-demultiplexed-seqs",
                f"{qiime_prefix}/demux.qza",
                "--p-trim-left-f",
                str(dada2.trim_left_f),
                "--p-trim-left-r",
                str(dada2.trim_left_r),
                "--p-trunc-len-f",
                str(dada2.trunc_len_f),
                "--p-trunc-len-r",
                str(dada2.trunc_len_r),
                "--p-n-threads",
                str(dada2.n_threads),
                "--o-table",
                f"{qiime_prefix}/table.qza",
                "--o-representative-sequences",
                f"{qiime_prefix}/rep-seqs.qza",
                "--o-denoising-stats",
                f"{qiime_prefix}/stats.qza",
            ],
            args.docker_platform,
        ),
        docker_run_command(
            base_dir,
            args.qiime2_image,
            [
                "qiime",
                "feature-table",
                "summarize",
                "--i-table",
                f"{qiime_prefix}/table.qza",
                "--o-visualization",
                f"{qiime_prefix}/table.qzv",
                "--m-sample-metadata-file",
                f"{qiime_prefix}/metadata.tsv",
            ],
            args.docker_platform,
        ),
        docker_run_command(
            base_dir,
            args.qiime2_image,
            [
                "qiime",
                "feature-table",
                "tabulate-seqs",
                "--i-data",
                f"{qiime_prefix}/rep-seqs.qza",
                "--o-visualization",
                f"{qiime_prefix}/rep-seqs.qzv",
            ],
            args.docker_platform,
        ),
        docker_run_command(
            base_dir,
            args.qiime2_image,
            [
                "qiime",
                "metadata",
                "tabulate",
                "--m-input-file",
                f"{qiime_prefix}/stats.qza",
                "--o-visualization",
                f"{qiime_prefix}/stats.qzv",
            ],
            args.docker_platform,
        ),
    ]

    for command in commands:
        run_command(command, args.dry_run)

    print("Would create:" if args.dry_run else "Created:")
    for output in outputs:
        print(f"- {output}")

    if not args.dry_run:
        write_run_report(
            qiime_dir / "dada2_run.json",
            config_path=config_path,
            config_sha256=config_sha256,
            base_dir=base_dir,
            qiime_dir=qiime_dir,
            command_line=sys.argv,
            commands=commands,
            qiime2_image=args.qiime2_image,
            docker_platform=args.docker_platform,
            dada2_values=dada2_values,
        )


if __name__ == "__main__":
    main()
