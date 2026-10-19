"""Validate and package the libraries for KiCad's Plugin and Content Manager."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = "com.github.autome-workspace.mas-connectors"
HOMEPAGE = "https://github.com/autome-workspace/MAS_connector_KicadLibrary"
PROPERTY = re.compile(r'(\(property\s+"(?:Footprint|ki_fp_filters)"\s+")([^"]*)(")')
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')


def without_models(source):
    """Remove complete model expressions, respecting quoted strings and nesting."""
    tokens = list(TOKEN.finditer(source))
    spans = []
    for i, token in enumerate(tokens[:-1]):
        if token.group() != "(" or tokens[i + 1].group() != "model":
            continue
        depth = 0
        for end in tokens[i:]:
            depth += (end.group() == "(") - (end.group() == ")")
            if depth == 0:
                spans.append((token.start(), end.end()))
                break
        else:
            raise ValueError("Unbalanced model expression")
    for start, end in reversed(spans):
        source = source[:start] + source[end:]
    return source


def inspect(symbols, footprints):
    errors = []
    for match in PROPERTY.finditer(symbols):
        for ref in match[2].split():
            if ":" not in ref:
                errors.append(f"Unqualified footprint reference: {ref}")
                continue
            library, name = ref.split(":", 1)
            if library == "MAS_V3":
                if name not in footprints:
                    errors.append(f"Missing packaged footprint: {ref}")
            elif library not in {"Connector_JST", "Connector_AMASS"}:
                errors.append(f"Unpackaged third-party footprint: {ref}")
    return sorted(set(errors))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check references without building")
    parser.add_argument("--version")
    parser.add_argument("--license", help="License chosen by the rights holder (no default)")
    parser.add_argument("--base-url", help="Public HTTPS directory for this version's release assets")
    parser.add_argument("--without-3d", action="store_true", help="Explicitly omit 3D references in the ZIP")
    args = parser.parse_args()
    symbols = (ROOT / "MAS_V3/MAS_V3.kicad_sym").read_text(encoding="utf-8")
    footprints = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "MAS_V3/MAS_V3.pretty").glob("*.kicad_mod"))
    }
    errors = inspect(symbols, footprints)
    model_count = sum(len(re.findall(r'\(model\s', text)) for text in footprints.values())
    print(f"Footprints: {len(footprints)}; 3D references: {model_count}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if model_count:
        print("3D models are not bundled. Building requires --without-3d.")
    if args.check:
        return 1 if errors else 0
    for field in ("version", "license", "base_url"):
        if not getattr(args, field):
            parser.error(f"--{field.replace('_', '-')} is required to build")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", args.version):
        parser.error("--version must contain 2 to 4 dot-separated numeric components")
    if not args.base_url.startswith("https://"):
        parser.error("--base-url must be HTTPS")
    if errors or (model_count and not args.without_3d):
        print("Build stopped: resolve the issues above before distributing.", file=sys.stderr)
        return 1

    # Match the default nickname prefix used by PCM auto-registration.
    symbols = PROPERTY.sub(
        lambda m: m[1] + m[2].replace("MAS_V3:", "PCM_MAS_V3:") + m[3], symbols
    )
    version = {"version": args.version, "status": "testing", "kicad_version": "10.0"}
    metadata = {
        "$schema": "https://go.kicad.org/pcm/schemas/v2",
        "name": "MAS Connector Libraries",
        "description": "Symbols and footprints for connectors defined by the MAS standard.",
        "description_full": "MAS connector symbol and footprint libraries. Requires the standard KiCad libraries. Uses the default PCM_ library nickname prefix. 3D models are not included.",
        "identifier": IDENTIFIER,
        "type": "library",
        "author": {"name": "autome-workspace", "contact": {"web": HOMEPAGE}},
        "license": args.license,
        "resources": {"homepage": HOMEPAGE},
        "versions": [version],
    }
    files = {"metadata.json": encode(metadata), "symbols/MAS_V3.kicad_sym": symbols.encode("utf-8")}
    for name, source in footprints.items():
        files[f"footprints/MAS_V3.pretty/{name}.kicad_mod"] = without_models(source).encode("utf-8")
    output = ROOT / "dist" / args.version
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"mas-connectors-{args.version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for name, data in files.items():
            package.writestr(name, data)
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("ZIP verification failed")
    base_url = args.base_url.rstrip("/")
    version.update({
        "download_url": f"{base_url}/{archive.name}",
        "download_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "download_size": archive.stat().st_size,
        "install_size": sum(map(len, files.values())),
    })
    packages = encode({"packages": [metadata]})
    (output / "packages.json").write_bytes(packages)
    repository = {
        "name": "MAS Connector Libraries",
        "packages": {
            "url": f"{base_url}/packages.json",
            "sha256": hashlib.sha256(packages).hexdigest(),
            "update_timestamp": int(time.time()),
        },
    }
    (output / "repository.json").write_bytes(encode(repository))
    print(f"Created {output}: upload all three files together.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
