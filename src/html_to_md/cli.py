"""Interface en ligne de commande : html2md INPUT [-o OUTPUT]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import MIN_IMAGE_BYTES
from .core import Result, process_file
from .extract import load_profiles

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "selectors.yaml"


def _iter_sources(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(p for p in input_path.rglob("*.html") if p.is_file())


def _output_dir(source: Path, input_path: Path, output_dir: Path) -> Path:
    """Sous-dossier de sortie reproduisant l'arborescence d'entrée."""
    if input_path.is_dir():
        return output_dir / source.relative_to(input_path).parent
    return output_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="html2md",
        description="Nettoie des captures SingleFile et les convertit en Markdown.",
    )
    parser.add_argument("input", type=Path, help="fichier .html ou dossier à traiter (récursif)")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("out"),
        help="dossier de sortie (défaut : ./out)",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="YAML des profils d'extraction (défaut : config/selectors.yaml)",
    )
    parser.add_argument(
        "--min-image-bytes", type=int, default=MIN_IMAGE_BYTES,
        help="taille minimale (octets) pour exporter une image data-URI au lieu de la supprimer",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        parser.error(f"introuvable : {args.input}")
    if not args.config.exists():
        parser.error(f"config introuvable : {args.config}")

    profiles = load_profiles(args.config)
    sources = _iter_sources(args.input)
    if not sources:
        print("Aucun fichier .html trouvé.", file=sys.stderr)
        return 1

    results: list[Result] = []
    taken: set[Path] = set()
    for source in sources:
        out_dir = _output_dir(source, args.input, args.output)
        try:
            result = process_file(
                source, out_dir, profiles,
                min_image_bytes=args.min_image_bytes, taken=taken,
            )
        except Exception as exc:  # un fichier corrompu ne doit pas stopper le lot
            result = Result(
                source=source, output=None, strategy="-", chars_in=0,
                chars_out=0, images=0, status="error", detail=str(exc),
            )
        results.append(result)
        _print_line(result)

    reviews = [r for r in results if r.status == "review"]
    errors = [r for r in results if r.status == "error"]
    print(
        f"\n{len(results)} fichier(s) traité(s) — "
        f"{len(results) - len(reviews) - len(errors)} ok, "
        f"{len(reviews)} à vérifier, {len(errors)} en erreur."
    )
    return 1 if errors else 0


def _print_line(r: Result) -> None:
    flag = {"ok": " ", "review": "?", "error": "!"}[r.status]
    info = f" [{r.detail}]" if r.detail else ""
    print(
        f"{flag} {r.source.name}  →  {r.output.name if r.output else '-'}"
        f"  ({r.strategy}, {r.chars_out} car., {r.images} img){info}"
    )


if __name__ == "__main__":
    sys.exit(main())
