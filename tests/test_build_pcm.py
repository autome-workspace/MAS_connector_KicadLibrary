import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location(
    "build_pcm", Path(__file__).resolve().parents[1] / "tools/build_pcm.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def test_package_references_and_repository_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "MAS_V3"
            pretty = library / "MAS_V3.pretty"
            pretty.mkdir(parents=True)
            symbols = '(property "Footprint" "MAS_V3:Part")\n(property "ki_fp_filters" "MAS_V3:Part Connector_JST:Standard")'
            footprint = '(footprint "Part" (model "C:/a (b)/part.wrl" (offset (xyz 0 0 0))) (pad "1" thru_hole circle))'
            (library / "MAS_V3.kicad_sym").write_text(symbols, encoding="utf-8")
            (pretty / "Part.kicad_mod").write_text(footprint, encoding="utf-8")
            args = ["build_pcm.py", "--version", "0.1.0", "--license", "TEST-ONLY",
                    "--base-url", "https://example.com/v0.1.0", "--without-3d"]
            with patch.object(builder, "ROOT", root), patch.object(sys, "argv", args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(builder.main(), 0)
            output = root / "dist/0.1.0"
            archive = output / "mas-connectors-0.1.0.zip"
            packages_bytes = (output / "packages.json").read_bytes()
            repository = json.loads((output / "repository.json").read_text())
            self.assertEqual(repository["packages"]["sha256"], hashlib.sha256(packages_bytes).hexdigest())
            version = json.loads(packages_bytes)["packages"][0]["versions"][0]
            self.assertEqual(version["download_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as package:
                packaged_symbols = package.read("symbols/MAS_V3.kicad_sym").decode()
                self.assertIn("PCM_MAS_V3:Part", packaged_symbols)
                self.assertIn("Connector_JST:Standard", packaged_symbols)
                self.assertNotIn("(model", package.read("footprints/MAS_V3.pretty/Part.kicad_mod").decode())
                self.assertIn('(pad "1"', package.read("footprints/MAS_V3.pretty/Part.kicad_mod").decode())
                embedded_version = json.loads(package.read("metadata.json"))["versions"][0]
                self.assertNotIn("download_sha256", embedded_version)
                self.assertEqual(version["install_size"], sum(i.file_size for i in package.infolist()))
            self.assertEqual((pretty / "Part.kicad_mod").read_text(encoding="utf-8"), footprint)

    def test_unbundled_footprints_block_distribution(self):
        source = '(property "Footprint" "MAS_V3:Missing") (property "Footprint" "JLCImport:Other")'
        errors = builder.inspect(source, {"Part": ""})
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("MAS_V3:Missing" in error for error in errors))
        self.assertTrue(any("JLCImport:Other" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
