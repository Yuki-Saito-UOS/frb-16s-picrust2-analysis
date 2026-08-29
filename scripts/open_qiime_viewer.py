from __future__ import annotations

import argparse
from pathlib import Path
import platform
import subprocess
import webbrowser


QIIME2_VIEW_URL = "https://view.qiime2.org/"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open QIIME2 View and print the selected .qzv path.")
    parser.add_argument("qzv", type=Path, help="Path to a QIIME2 .qzv visualization.")
    parser.add_argument("--no-browser", action="store_true", help="Print the URL without opening a browser.")
    parser.add_argument("--no-folder", action="store_true", help="Do not open the folder containing the .qzv file.")
    return parser


def open_qzv_folder(qzv: Path) -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", "-R", str(qzv)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", f"/select,{qzv}"], check=True)
        else:
            subprocess.run(["xdg-open", str(qzv.parent)], check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def main() -> None:
    args = build_parser().parse_args()
    qzv = args.qzv.expanduser().resolve()

    if not qzv.exists():
        raise SystemExit(f"QZV file not found: {qzv}")
    if qzv.suffix != ".qzv":
        raise SystemExit(f"Expected a .qzv file: {qzv}")

    print("QIIME2 View:")
    print(f"- url: {QIIME2_VIEW_URL}")
    print(f"- qzv: {qzv}")
    print("")
    print("ブラウザで QIIME2 View が開いたら、上の .qzv ファイルをドラッグ&ドロップして確認してください。")
    print("外部サイトへのアップロードになるため、自動アップロードは行いません。")
    print("macOS では Finder、Windows では Explorer、Linux では既定のファイルマネージャを開きます。")

    if not args.no_folder:
        opened_folder = open_qzv_folder(qzv)
        if not opened_folder:
            print("")
            print("フォルダを自動で開けませんでした。上の .qzv パスを手動で開いてください。")

    if not args.no_browser:
        opened = webbrowser.open(QIIME2_VIEW_URL)
        if not opened:
            print("")
            print("ブラウザを自動で開けませんでした。上の URL を手動で開いてください。")


if __name__ == "__main__":
    main()
