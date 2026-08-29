from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ricebran_analysis.config import load_config
from ricebran_analysis.raw import scan_paired_fastq, write_qiime_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build QIIME2 manifest and sample metadata from paired FASTQ files.")
    parser.add_argument("--config", type=Path, default=Path("config/frb.toml"))
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    raw_dir = args.raw_dir.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()

    pairs = scan_paired_fastq(raw_dir, config.groups)
    outputs = write_qiime_manifest(raw_dir, out_dir, config)

    print(f"paired_samples={len(pairs)}")
    for pair in pairs:
        print(f"- {pair.sample}\t{pair.group or 'unknown'}")
    print("Saved:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
