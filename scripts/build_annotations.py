from __future__ import annotations

import argparse
import gzip
from html import unescape
from pathlib import Path
import re
import shutil
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ricebran_analysis.config import ProjectPaths, load_config
from ricebran_analysis.feature_analysis import write_feature_outputs


KEGG_KO_LIST = "https://rest.kegg.jp/list/ko"
KEGG_ENZYME_LIST = "https://rest.kegg.jp/list/enzyme"
KEGG_KO_ENZYME_LINK = "https://rest.kegg.jp/link/enzyme/ko"
EXPASY_ENZYME_DAT = "https://ftp.expasy.org/databases/enzyme/enzyme.dat"
BIOCYC_GETXML = "https://websvc.biocyc.org/getxml?META:{pathway_id}"

RANKS = [
    ("domain", "d__"),
    ("phylum", "p__"),
    ("class", "c__"),
    ("order", "o__"),
    ("family", "f__"),
    ("genus", "g__"),
    ("species", "s__"),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build public-database annotations for QIIME2/PICRUSt2 outputs.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--fetch-metacyc", action="store_true", help="Fetch missing MetaCyc pathway names from BioCyc.")
    return parser


def fetch_text(url: str, path: Path, *, force: bool = False) -> str:
    if path.exists() and not force:
        return path.read_text()

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(url, timeout=60) as response:
            text = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as exc:
        if path.exists():
            return path.read_text()
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc

    path.write_text(text)
    return text


def fetch_biocyc_common_name(pathway_id: str, path: Path, *, force: bool = False, fetch: bool = False) -> tuple[str, str]:
    if path.exists() and not force:
        return path.read_text().strip(), "BioCyc getxml cached common-name"

    url = BIOCYC_GETXML.format(pathway_id=pathway_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy_xml = path.parent.parent / "metacyc_xml" / f"{pathway_id}.xml"
    if legacy_xml.exists() and not force:
        text = legacy_xml.read_text(errors="replace")
        match = re.search(r"<common-name[^>]*>(.*?)</common-name>", text, flags=re.S)
        if match:
            name = unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
            path.write_text(name)
            return name, "BioCyc getxml legacy XML cache"

    if not fetch:
        return "", "MetaCyc name missing from local cache"

    try:
        with urlopen(url, timeout=15) as response:
            chunks: list[bytes] = []
            total = 0
            while total < 300_000:
                chunk = response.read(1024)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                text = b"".join(chunks).decode("utf-8", errors="replace")
                match = re.search(r"<common-name[^>]*>(.*?)</common-name>", text, flags=re.S)
                if match:
                    name = unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
                    path.write_text(name)
                    return name, "BioCyc getxml common-name"
    except (HTTPError, URLError, TimeoutError) as exc:
        if path.exists():
            return path.read_text().strip(), f"BioCyc getxml cached after error: {exc}"
        return "", f"BioCyc getxml failed: {exc}"
    return "", "BioCyc getxml common-name not found"


def parse_kegg_ko(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        ko, desc = line.split("\t", 1)
        ko = ko.replace("ko:", "")
        ecs = sorted(set(re.findall(r"EC:([0-9.-]+)", desc)))
        desc_no_ec = re.sub(r"\s*\[EC:[^\]]+\]\s*", "", desc).strip()
        if ";" in desc_no_ec:
            genes, name = desc_no_ec.split(";", 1)
        else:
            genes, name = "", desc_no_ec
        rows.append(
            {
                "ko": ko,
                "gene_symbols": genes.strip(),
                "ko_name": name.strip(),
                "ec_numbers": ";".join(ecs),
                "source": "KEGG REST list/ko",
            }
        )
    return pd.DataFrame(rows)


def parse_kegg_enzymes(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        ec, desc = line.split("\t", 1)
        transferred_to = sorted(set(re.findall(r"\b[0-9]+\.[0-9]+\.[0-9]+\.[0-9-]+\b", desc)))
        status = "current"
        if desc.lower().startswith("transferred"):
            status = "transferred"
        elif desc.lower().startswith("deleted"):
            status = "deleted"
        rows.append(
            {
                "ec": ec.replace("ec:", ""),
                "enzyme_name": desc.strip(),
                "status": status,
                "transferred_to": ";".join(transferred_to),
                "source": "KEGG REST list/enzyme",
            }
        )
    return pd.DataFrame(rows)


def parse_ko_enzyme_links(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        ko, ec = line.split("\t", 1)
        rows.append({"ko": ko.replace("ko:", ""), "ec": ec.replace("ec:", "")})
    return pd.DataFrame(rows)


def parse_expasy_transfers(text: str) -> pd.DataFrame:
    rows = []
    current: dict[str, list[str] | str] | None = None
    for line in text.splitlines():
        if line.startswith("ID   "):
            current = {"ec": line[5:].strip(), "de": [], "an": []}
        elif line.startswith("DE   ") and current is not None:
            current["de"].append(line[5:].strip())
        elif line.startswith("AN   ") and current is not None:
            current["an"].append(line[5:].strip())
        elif line == "//" and current is not None:
            de = " ".join(current["de"]).strip()
            transferred_to = sorted(set(re.findall(r"\b[0-9]+\.[0-9]+\.[0-9]+\.[0-9-]+\b", de)))
            status = "current"
            if "transferred" in de.lower():
                status = "transferred"
            elif "deleted" in de.lower():
                status = "deleted"
            rows.append(
                {
                    "ec": str(current["ec"]),
                    "expasy_name": de.rstrip("."),
                    "expasy_alt_names": " ".join(current["an"]).strip(),
                    "expasy_status": status,
                    "expasy_transferred_to": ";".join(transferred_to),
                    "expasy_source": "ENZYME enzyme.dat",
                }
            )
            current = None
    return pd.DataFrame(rows)


def read_table(path: Path) -> pd.DataFrame:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        return pd.read_csv(handle, sep="\t")


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def copy_without_sidecar(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    (dst.parent / f"._{dst.name}").unlink(missing_ok=True)


def parse_taxon(taxon: str) -> dict[str, str]:
    parsed = {name: "" for name, _ in RANKS}
    for part in str(taxon).split(";"):
        part = part.strip()
        for name, prefix in RANKS:
            if part.startswith(prefix):
                value = part.replace(prefix, "", 1).strip()
                parsed[name] = "" if value.lower() in {"", "uncultured", "unidentified"} else value
    return parsed


def resolved_taxon_label(parsed: dict[str, str]) -> tuple[str, str]:
    genus = parsed.get("genus", "")
    species = parsed.get("species", "")
    family = parsed.get("family", "")
    if genus and species:
        species_tail = species.split()[-1]
        return f"{genus}_{species_tail}", "species"
    if genus:
        return genus, "genus"
    if family:
        return f"F_{family}", "family"
    for rank in ["order", "class", "phylum", "domain"]:
        if parsed.get(rank):
            return parsed[rank], rank
    return "Unassigned", "unassigned"


def build_taxonomy_annotations(taxonomy_path: Path, feature_table_path: Path, out_dir: Path) -> pd.DataFrame:
    taxonomy = pd.read_csv(taxonomy_path, sep="\t")
    rows = []
    for _, row in taxonomy.iterrows():
        parsed = parse_taxon(row["Taxon"])
        label, rank = resolved_taxon_label(parsed)
        rows.append(
            {
                "feature_id": row["Feature ID"],
                "taxon_label": label,
                "taxon_rank": rank,
                "original_taxon": row["Taxon"],
                "confidence": row.get("Confidence", ""),
                **parsed,
            }
        )
    annotations = pd.DataFrame(rows)
    write_table(annotations, out_dir / "taxonomy_annotations.tsv")

    feature_table = pd.read_csv(feature_table_path, sep="\t", skiprows=1)
    feature_col = feature_table.columns[0]
    feature_table = feature_table.rename(columns={feature_col: "feature_id"})
    merged = feature_table.merge(annotations[["feature_id", "taxon_label"]], on="feature_id", how="left")
    sample_cols = [c for c in merged.columns if c not in {"feature_id", "taxon_label"}]
    resolved = merged.groupby("taxon_label", as_index=True)[sample_cols].sum(numeric_only=True)
    resolved = resolved.reset_index().rename(columns={"taxon_label": "taxon"})
    write_table(resolved, out_dir / "table-taxonomy-resolved.tsv")
    return resolved.set_index("taxon").T.rename_axis("sample")


def pathway_ids(paths: ProjectPaths, results_dir: Path) -> list[str]:
    ids: set[str] = set()
    path_table = read_table(paths.pathway_unstrat)
    ids.update(path_table.iloc[:, 0].astype(str))
    for stats_path in results_dir.glob("pathway_stats_*.tsv"):
        df = pd.read_csv(stats_path, sep="\t")
        if "pathway" in df.columns:
            ids.update(df["pathway"].astype(str))
    for top_path in results_dir.glob("TOP_pathways_*.tsv"):
        df = pd.read_csv(top_path, sep="\t")
        if "pathway" in df.columns:
            ids.update(df["pathway"].astype(str))
    return sorted(ids)


def fetch_metacyc_name(pathway_id: str, cache_dir: Path, force: bool, fetch: bool) -> dict[str, str]:
    name_path = cache_dir / "metacyc_names" / f"{pathway_id}.txt"
    url = BIOCYC_GETXML.format(pathway_id=pathway_id)
    name, source = fetch_biocyc_common_name(pathway_id, name_path, force=force, fetch=fetch)
    return {"pathway": pathway_id, "pathway_name": name, "metacyc_url": url, "pathway_source": source}


def parse_pathway_reactions(parsed_mapfile: Path) -> pd.DataFrame:
    rows = []
    with parsed_mapfile.open() as handle:
        for line in handle:
            parts = line.strip().split()
            if not parts:
                continue
            pathway, reactions = parts[0], parts[1:]
            ec_numbers = sorted(
                {
                    match.group(1)
                    for reaction in reactions
                    for match in [re.match(r"^([0-9]+\.[0-9]+\.[0-9]+\.[0-9-]+)-RXN$", reaction)]
                    if match
                }
            )
            rows.append(
                {
                    "pathway": pathway,
                    "reaction_count": len(reactions),
                    "reaction_ids": ";".join(reactions),
                    "reaction_ec_numbers": ";".join(ec_numbers),
                }
            )
    return pd.DataFrame(rows)


def parse_picrust2_pathway_info(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["pathway", "pathway_name", "pathway_source"])
    rows = []
    with path.open() as handle:
        for line in handle:
            if not line.strip() or "\t" not in line:
                continue
            pathway, name = line.rstrip("\n").split("\t", 1)
            rows.append(
                {
                    "pathway": pathway,
                    "pathway_name": name,
                    "pathway_source": "PICRUSt2 metacyc_pathways_info.txt.gz",
                }
            )
    return pd.DataFrame(rows)


def annotate_function_table(table_path: Path, annotation: pd.DataFrame, key: str, out_path: Path) -> None:
    df = read_table(table_path)
    first = df.columns[0]
    df = df.rename(columns={first: key})
    annotated = df.merge(annotation, on=key, how="left")
    sample_cols = [c for c in df.columns if c != key]
    anno_cols = [c for c in annotated.columns if c not in {key, *sample_cols}]
    write_table(annotated[[key, *anno_cols, *sample_cols]], out_path)


def annotate_result_tables(results_dir: Path, annotation: pd.DataFrame, key: str) -> None:
    for path in results_dir.glob(f"{key}_stats_*.tsv"):
        if path.name.startswith("annotated_"):
            continue
        df = pd.read_csv(path, sep="\t")
        if key not in df.columns:
            continue
        annotated = df.merge(annotation, on=key, how="left")
        write_table(annotated, results_dir / f"annotated_{path.name}")
    for path in results_dir.glob(f"TOP_{key}*.tsv"):
        if path.name.startswith("annotated_"):
            continue
        df = pd.read_csv(path, sep="\t")
        if key not in df.columns:
            continue
        annotated = df.merge(annotation, on=key, how="left")
        write_table(annotated, results_dir / f"annotated_{path.name}")


def build_annotations(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    paths = ProjectPaths(
        base_dir=args.base_dir.expanduser().resolve(),
        out_dir=args.results_dir.resolve(),
        qiime_dirname=config.qiime_dirname,
        picrust2_dirname=config.picrust2_dirname,
        results_dirname=config.results_dirname,
    )
    cache_dir = (args.cache_dir or (paths.base_dir / "annotation_cache")).expanduser().resolve()
    out_dir = args.results_dir.resolve() / "annotations"
    out_dir.mkdir(parents=True, exist_ok=True)

    ko = parse_kegg_ko(fetch_text(KEGG_KO_LIST, cache_dir / "kegg_ko.tsv", force=args.force_download))
    enzymes = parse_kegg_enzymes(
        fetch_text(KEGG_ENZYME_LIST, cache_dir / "kegg_enzyme.tsv", force=args.force_download)
    )
    links = parse_ko_enzyme_links(
        fetch_text(KEGG_KO_ENZYME_LINK, cache_dir / "kegg_ko_enzyme.tsv", force=args.force_download)
    )
    expasy = parse_expasy_transfers(
        fetch_text(EXPASY_ENZYME_DAT, cache_dir / "enzyme.dat", force=args.force_download)
    )

    ec_annotation = enzymes.merge(expasy, on="ec", how="outer")
    ec_annotation["enzyme_name"] = ec_annotation["enzyme_name"].fillna(ec_annotation["expasy_name"])
    ec_annotation["status"] = ec_annotation["status"].fillna(ec_annotation["expasy_status"]).fillna("unknown")
    ec_annotation["transferred_to"] = ec_annotation["transferred_to"].fillna(ec_annotation["expasy_transferred_to"])
    write_table(ec_annotation, out_dir / "ec_annotations.tsv")

    linked_ec = links.groupby("ko")["ec"].apply(lambda s: ";".join(sorted(set(s)))).reset_index()
    ko_annotation = ko.merge(linked_ec, on="ko", how="outer", suffixes=("", "_linked"))
    linked_col = "ec_linked" if "ec_linked" in ko_annotation.columns else "ec"
    ko_annotation["ec_numbers"] = ko_annotation["ec_numbers"].fillna(ko_annotation[linked_col]).fillna("")
    ec_status = ec_annotation.set_index("ec")[["status", "transferred_to"]].to_dict("index")

    def summarize_ecs(ec_text: str) -> pd.Series:
        ecs = [ec for ec in str(ec_text).split(";") if ec]
        statuses = sorted({ec_status.get(ec, {}).get("status", "unknown") for ec in ecs})
        transferred = sorted(
            {
                target
                for ec in ecs
                for target in str(ec_status.get(ec, {}).get("transferred_to", "")).split(";")
                if target
            }
        )
        return pd.Series({"ec_status_summary": ";".join(statuses), "transferred_ec_numbers": ";".join(transferred)})

    if not ko_annotation.empty:
        ko_annotation = pd.concat([ko_annotation, ko_annotation["ec_numbers"].apply(summarize_ecs)], axis=1)
    ko_annotation = ko_annotation.drop(columns=[c for c in ["ec", "ec_linked"] if c in ko_annotation])
    write_table(ko_annotation, out_dir / "ko_annotations.tsv")

    reaction_annotation = parse_pathway_reactions(paths.picrust2_dir / "intermediate" / "pathways" / "parsed_mapfile.tsv")
    biocyc_annotation = pd.DataFrame(
        [fetch_metacyc_name(pid, cache_dir, args.force_download, args.fetch_metacyc) for pid in pathway_ids(paths, args.results_dir)]
    )
    picrust2_pathway_info = parse_picrust2_pathway_info(cache_dir / "picrust2_metacyc_pathways_info.tsv")
    pathway_annotation = biocyc_annotation.merge(
        picrust2_pathway_info,
        on="pathway",
        how="left",
        suffixes=("_biocyc", "_picrust2"),
    )
    pathway_annotation["pathway_name"] = pathway_annotation["pathway_name_picrust2"].fillna(
        pathway_annotation["pathway_name_biocyc"]
    )
    pathway_annotation["pathway_source"] = pathway_annotation["pathway_source_picrust2"].fillna(
        pathway_annotation["pathway_source_biocyc"]
    )
    pathway_annotation = pathway_annotation.drop(
        columns=[
            "pathway_name_biocyc",
            "pathway_name_picrust2",
            "pathway_source_biocyc",
            "pathway_source_picrust2",
        ]
    )
    pathway_annotation = pathway_annotation.merge(reaction_annotation, on="pathway", how="left")
    write_table(pathway_annotation, out_dir / "pathway_annotations.tsv")

    taxon_table = build_taxonomy_annotations(
        paths.qiime_dir / "exported-taxonomy" / "taxonomy.tsv",
        paths.qiime_dir / "table.tsv",
        out_dir,
    )
    write_feature_outputs(taxon_table, "taxon", "taxon", "taxa", args.results_dir.resolve(), config)

    annotate_result_tables(args.results_dir.resolve(), pathway_annotation, "pathway")
    annotate_function_table(
        paths.picrust2_dir / "pathways_out" / "path_abun_unstrat.tsv.gz",
        pathway_annotation,
        "pathway",
        out_dir / "path_abun_unstrat_annotated.tsv",
    )
    ec_function_annotation = ec_annotation.rename(columns={"ec": "ec_number"}).copy()
    ec_function_annotation["function"] = "EC:" + ec_function_annotation["ec_number"].astype(str)
    annotate_function_table(
        paths.picrust2_dir / "EC_metagenome_out" / "pred_metagenome_unstrat.tsv.gz",
        ec_function_annotation,
        "function",
        out_dir / "ec_metagenome_unstrat_annotated.tsv",
    )
    annotate_function_table(
        paths.picrust2_dir / "KO_metagenome_out" / "pred_metagenome_unstrat.tsv.gz",
        ko_annotation.rename(columns={"ko": "function"}),
        "function",
        out_dir / "ko_metagenome_unstrat_annotated.tsv",
    )

    external_results = paths.configured_results_dir
    for path in args.results_dir.resolve().glob("annotated_*.tsv"):
        copy_without_sidecar(path, external_results / path.name)
    for path in args.results_dir.resolve().glob("taxon*.tsv"):
        copy_without_sidecar(path, external_results / path.name)
    for path in args.results_dir.resolve().glob("TOP_taxa*.tsv"):
        copy_without_sidecar(path, external_results / path.name)
    for path in out_dir.glob("*.tsv"):
        copy_without_sidecar(path, external_results / "annotations" / path.name)

    print(f"Saved annotations to: {out_dir}")
    print(f"Mirrored annotations to: {external_results / 'annotations'}")
    print(f"Saved taxon stats to: {args.results_dir.resolve()}")


def main() -> None:
    build_annotations(build_parser().parse_args())


if __name__ == "__main__":
    main()
