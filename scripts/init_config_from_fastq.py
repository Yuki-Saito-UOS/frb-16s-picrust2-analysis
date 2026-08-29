from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import re


FASTQ_RE = re.compile(r"^(?P<sample>.+)_R[12](?:_\d+)?\.(?:fastq|fq)(?:\.gz)?$", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an analysis config TOML from FASTQ filenames.")
    parser.add_argument("--target", required=True, help="Analysis target name.")
    parser.add_argument("--base-dir", type=Path, required=True, help="Directory containing the raw FASTQ directory.")
    parser.add_argument("--out", type=Path, help="Output config TOML path. Defaults to config/<target>.toml.")
    parser.add_argument("--raw-dirname", help="Raw FASTQ directory name. Defaults to <target>_raw.")
    parser.add_argument("--qiime-dirname", help="QIIME2 output directory name. Defaults to <target>_QIIME.")
    parser.add_argument("--results-dirname", help="Results directory name. Defaults to <target>_results.")
    parser.add_argument("--picrust2-dirname", default="picrust2_out")
    parser.add_argument(
        "--group-alias",
        action="append",
        default=[],
        metavar="FROM=TO",
        help="Rename inferred group labels, e.g. old_group=new_group. Can be used multiple times.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite output config if it already exists.")
    return parser


def parse_group_aliases(values: list[str]) -> dict[str, str]:
    aliases = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Invalid --group-alias value: {value}. Expected FROM=TO.")
        source, target = value.split("=", 1)
        source = source.strip()
        target = target.strip()
        if not source or not target:
            raise SystemExit(f"Invalid --group-alias value: {value}. Expected FROM=TO.")
        aliases[source] = target
    return aliases


def infer_group(sample: str, aliases: dict[str, str]) -> str:
    group = re.sub(r"\d+$", "", sample)
    return aliases.get(group, group)


def find_samples(raw_dir: Path) -> list[str]:
    samples = set()
    read_counts: dict[str, set[str]] = defaultdict(set)

    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name.startswith("._"):
            continue
        match = FASTQ_RE.match(path.name)
        if match is None:
            continue
        sample = match.group("sample")
        read = "_R1" if "_R1" in path.name else "_R2"
        read_counts[sample].add(read)
        samples.add(sample)

    paired = [sample for sample in samples if {"_R1", "_R2"}.issubset(read_counts[sample])]
    return sorted(paired)


def quote_list(values: list[str]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def write_config(
    out: Path,
    target: str,
    raw_dirname: str,
    qiime_dirname: str,
    results_dirname: str,
    picrust2_dirname: str,
    groups: dict[str, list[str]],
) -> None:
    lines = [
        "[project]",
        f'target = "{target}"',
        f'raw_dirname = "{raw_dirname}"',
        f'qiime_dirname = "{qiime_dirname}"',
        f'results_dirname = "{results_dirname}"',
        f'picrust2_dirname = "{picrust2_dirname}"',
        f'docker_raw_dir = "/work/{raw_dirname}"',
        "",
        "[groups]",
    ]
    for group in sorted(groups):
        lines.append(f"{group} = {quote_list(groups[group])}")

    lines.extend(
        [
            "",
            "[thresholds]",
            "p_value = 0.05",
            "effect = 0.20",
            "top_n = 30",
            "",
            "[qiime2.dada2]",
            "trim_left_f = 0",
            "trim_left_r = 0",
            "trunc_len_f = 290",
            "trunc_len_r = 290",
            "n_threads = 4",
            "",
            "[qiime2.feature_filter]",
            "min_frequency = 10",
            "min_samples = 2",
            "",
            "[qiime2.rarefaction]",
            "# rarefaction を使う場合、alpha-rarefaction.qzv を確認してから設定する。",
            "# sampling_depth = 10000",
            "",
            "[picrust2]",
            "# 高 NSTI の予測を除外する場合だけ設定する。",
            "# max_nsti = 2.0",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))


def main() -> None:
    args = build_parser().parse_args()
    target = args.target
    base_dir = args.base_dir.expanduser().resolve()
    raw_dirname = args.raw_dirname or f"{target}_raw"
    qiime_dirname = args.qiime_dirname or f"{target}_QIIME"
    results_dirname = args.results_dirname or f"{target}_results"
    raw_dir = base_dir / raw_dirname
    out = (args.out or Path("config") / f"{target}.toml").expanduser().resolve()

    if out.exists() and not args.force:
        raise SystemExit(f"Output config already exists. Use --force to overwrite: {out}")
    if not raw_dir.exists():
        raise SystemExit(f"Raw FASTQ directory not found: {raw_dir}")

    aliases = parse_group_aliases(args.group_alias)
    samples = find_samples(raw_dir)
    if not samples:
        raise SystemExit(f"No paired FASTQ samples found: {raw_dir}")

    groups: dict[str, list[str]] = defaultdict(list)
    for sample in samples:
        groups[infer_group(sample, aliases)].append(sample)

    write_config(
        out,
        target=target,
        raw_dirname=raw_dirname,
        qiime_dirname=qiime_dirname,
        results_dirname=results_dirname,
        picrust2_dirname=args.picrust2_dirname,
        groups=dict(groups),
    )

    print(f"Wrote: {out}")
    print("Detected groups:")
    for group in sorted(groups):
        print(f"- {group}: {len(groups[group])} samples")
        for sample in groups[group]:
            print(f"  - {sample}")
    print("")
    print("Review [groups] before running analysis.")


if __name__ == "__main__":
    main()
