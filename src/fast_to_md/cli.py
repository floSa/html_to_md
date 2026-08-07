"""Interface en ligne de commande : fast2md INPUT [-o OUTPUT]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import MIN_IMAGE_BYTES
from .core import Result, process_file
from .extract import load_profiles
from .sources import SUPPORTED_EXTENSIONS, iter_sources

CONFIG_NAME = Path("config") / "selectors.yaml"

# Emplacements essayés quand aucun --config n'est donné : la racine du dépôt
# (installation en mode développement) puis le dossier courant. Une fois le
# paquet installé ailleurs, le premier chemin ne pointe plus sur rien — d'où
# le second, et le repli sans profil.
DEFAULT_CONFIG_PATHS = (
    Path(__file__).resolve().parents[2] / CONFIG_NAME,
    Path.cwd() / CONFIG_NAME,
)


def _default_config() -> Path | None:
    """Premier fichier de profils trouvé, ou ``None`` s'il n'y en a pas."""
    return next((path for path in DEFAULT_CONFIG_PATHS if path.is_file()), None)


def _iter_sources(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return iter_sources(input_path)


def _output_dir(source: Path, input_path: Path, output_dir: Path) -> Path:
    """Sous-dossier de sortie reproduisant l'arborescence d'entrée."""
    if input_path.is_dir():
        return output_dir / source.relative_to(input_path).parent
    return output_dir


def main(argv: list[str] | None = None) -> int:
    formats = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    parser = argparse.ArgumentParser(
        prog="fast2md",
        description=(
            "Convertit des documents en Markdown propre "
            f"(formats pris en charge : {formats})."
        ),
    )
    parser.add_argument("input", type=Path, help="fichier ou dossier à traiter (récursif)")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("out"),
        help="dossier de sortie (défaut : ./out)",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help=(
            f"YAML des profils d'extraction (défaut : {CONFIG_NAME} s'il existe, "
            "sinon mode générique sans profil)"
        ),
    )
    parser.add_argument(
        "--min-image-bytes", type=int, default=MIN_IMAGE_BYTES,
        help=(
            "taille minimale (octets) pour exporter une image au lieu de la "
            "supprimer ; ne s'applique qu'aux pages web, dont il écarte les "
            "icônes d'interface"
        ),
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        parser.error(f"introuvable : {args.input}")
    # Une config demandée explicitement et absente est une erreur ; une config
    # par défaut absente ne l'est pas — les profils sont optionnels.
    if args.config is not None and not args.config.is_file():
        parser.error(f"config introuvable : {args.config}")

    config = args.config or _default_config()
    profiles = load_profiles(config) if config else []
    sources = _iter_sources(args.input)
    if not sources:
        print(f"Aucun fichier convertible trouvé ({formats}).", file=sys.stderr)
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
