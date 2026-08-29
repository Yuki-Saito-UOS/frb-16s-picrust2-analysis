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
from ricebran_analysis.raw import scan_paired_fastq, write_qiime_manifest


DEFAULT_QIIME2_IMAGE = "quay.io/qiime2/amplicon@sha256:4038fd785bf4e76ddd6ec7a7f57abe94cdca6c5cd0a93d0924971a74eabd7cf2"
DEFAULT_DOCKER_PLATFORM = "linux/amd64"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build QIIME2 manifest, import paired reads, and create demux.qzv."
    )
    parser.add_argument("--config", type=Path, required=True, help="Analysis config TOML.")
    parser.add_argument("--base-dir", type=Path, required=True, help="Directory mounted as /work in Docker.")
    parser.add_argument("--qiime2-image", default=DEFAULT_QIIME2_IMAGE)
    parser.add_argument("--docker-platform", default=DEFAULT_DOCKER_PLATFORM)
    parser.add_argument("--open-viewer", action="store_true", help="Open QIIME2 View after demux.qzv is created.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running Docker.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing manifest, metadata, demux.qza, and demux.qzv.")
    return parser


def docker_run_command(
    base_dir: Path,
    image: str,
    qiime_args: list[str],
    docker_platform: str | None = None,
) -> list[str]:
    command = ["docker", "run", "--rm"]
    if docker_platform:
        command.extend(["--platform", docker_platform])
    command.extend(["-v", f"{base_dir}:/work", image, *qiime_args])
    return command


def run_command(command: list[str], dry_run: bool) -> None:
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, check=True)


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


def refuse_existing(paths: list[Path], force: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        print("Refusing to overwrite existing outputs. Use --force to overwrite:")
        for path in existing:
            print(f"- {path}")
        raise SystemExit(1)


def fastq_record(path: Path, docker_raw_dir: str | None) -> dict[str, object]:
    docker_path = f"{docker_raw_dir.rstrip('/')}/{path.name}" if docker_raw_dir else str(path)
    stat = path.stat()
    return {
        "name": path.name,
        "local_path": str(path),
        "docker_path": docker_path,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def write_run_report(
    report_path: Path,
    *,
    config_path: Path,
    base_dir: Path,
    raw_dir: Path,
    qiime_dir: Path,
    config_sha256: str,
    command_line: list[str],
    import_command: list[str],
    summarize_command: list[str],
    qiime2_image: str,
    docker_platform: str | None,
    pairs,
    docker_raw_dir: str | None,
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
            "raw_dir": str(raw_dir),
            "qiime_dir": str(qiime_dir),
            "manifest": str(qiime_dir / "manifest.tsv"),
            "metadata": str(qiime_dir / "metadata.tsv"),
            "demux_qza": str(qiime_dir / "demux.qza"),
            "demux_qzv": str(qiime_dir / "demux.qzv"),
        },
        "docker": {
            "platform": docker_platform,
            "qiime2_image": qiime2_image,
            "import_command": import_command,
            "summarize_command": summarize_command,
        },
        "samples": [
            {
                "sample": pair.sample,
                "group": pair.group,
                "forward": fastq_record(pair.forward, docker_raw_dir),
                "reverse": fastq_record(pair.reverse, docker_raw_dir),
            }
            for pair in pairs
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    args = build_parser().parse_args()
    config_path = args.config.expanduser().resolve()
    base_dir = args.base_dir.expanduser().resolve()
    config = load_config(config_path)

    raw_dir = base_dir / config.raw_dirname
    qiime_dir = base_dir / config.qiime_dirname
    manifest = qiime_dir / "manifest.tsv"
    metadata = qiime_dir / "metadata.tsv"
    local_demux_qza = qiime_dir / "demux.qza"
    local_demux_qzv = qiime_dir / "demux.qzv"
    report_path = qiime_dir / "prepare_demux_run.json"
    manifest_path = f"/work/{config.qiime_dirname}/manifest.tsv"
    demux_qza = f"/work/{config.qiime_dirname}/demux.qza"
    demux_qzv = f"/work/{config.qiime_dirname}/demux.qzv"
    config_sha256 = sha256_file(config_path)

    print("Prepare demux")
    print(f"- config: {config_path}")
    print(f"- config_sha256: {config_sha256}")
    print(f"- base_dir: {base_dir}")
    print(f"- raw_dir: {raw_dir}")
    print(f"- qiime_dir: {qiime_dir}")
    print(f"- docker_raw_dir: {config.docker_raw_dir or '(local absolute paths)'}")
    print(f"- qiime2_image: {args.qiime2_image}")
    print(f"- docker_platform: {args.docker_platform or '(default)'}")

    pairs = scan_paired_fastq(raw_dir, config.groups)
    if not pairs:
        raise SystemExit(f"No paired FASTQ files found: {raw_dir}")
    refuse_existing([manifest, metadata, local_demux_qza, local_demux_qzv, report_path], args.force or args.dry_run)

    print(f"paired_samples={len(pairs)}")
    for pair in pairs:
        print(f"- {pair.sample}\t{pair.group or 'unknown'}")
    if args.dry_run:
        print("Would save:")
        print(f"- manifest: {manifest}")
        print(f"- metadata: {metadata}")
    else:
        outputs = write_qiime_manifest(raw_dir, qiime_dir, config)
        print("Saved:")
        for name, path in outputs.items():
            print(f"- {name}: {path}")

    import_command = docker_run_command(
        base_dir,
        args.qiime2_image,
        [
            "qiime",
            "tools",
            "import",
            "--type",
            "SampleData[PairedEndSequencesWithQuality]",
            "--input-path",
            manifest_path,
            "--output-path",
            demux_qza,
            "--input-format",
            "PairedEndFastqManifestPhred33V2",
        ],
        args.docker_platform,
    )
    run_command(import_command, args.dry_run)

    summarize_command = docker_run_command(
        base_dir,
        args.qiime2_image,
        [
            "qiime",
            "demux",
            "summarize",
            "--i-data",
            demux_qza,
            "--o-visualization",
            demux_qzv,
        ],
        args.docker_platform,
    )
    run_command(summarize_command, args.dry_run)

    print("Would create:" if args.dry_run else "Created:")
    print(f"- {local_demux_qzv}")

    if not args.dry_run:
        write_run_report(
            report_path,
            config_path=config_path,
            base_dir=base_dir,
            raw_dir=raw_dir,
            qiime_dir=qiime_dir,
            config_sha256=config_sha256,
            command_line=sys.argv,
            import_command=import_command,
            summarize_command=summarize_command,
            qiime2_image=args.qiime2_image,
            docker_platform=args.docker_platform,
            pairs=pairs,
            docker_raw_dir=config.docker_raw_dir,
        )
        print(f"- run_report: {report_path}")

    if args.open_viewer and not args.dry_run:
        viewer_script = Path(__file__).resolve().parent / "open_qiime_viewer.py"
        subprocess.run([sys.executable, str(viewer_script), str(local_demux_qzv)], check=True)


if __name__ == "__main__":
    main()
