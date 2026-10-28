"""Pure release identity and source-license checks; never builds, installs or publishes."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    builder = root / "ShopController/scripts/publish_release.py"
    spec = importlib.util.spec_from_file_location("release_builder_fixture", builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads((root / "ShopController/extension/manifest.json").read_text(encoding="utf-8-sig"))
    expected = "".join(chr(ord("a") + nibble) for byte in hashlib.sha256(base64.b64decode(manifest["key"], validate=True)).digest()[:16]
                       for nibble in (byte >> 4, byte & 15))
    assert module.extension_id_from_key(manifest["key"]) == expected
    assert len(expected) == 32 and all("a" <= c <= "p" for c in expected)
    print("PASS fixed public manifest key produces the independently calculated Chrome extension ID")
    invalid = [None, "", "not valid base64!", base64.b64encode(b"short").decode(), base64.b64encode(b"X" * 64).decode()]
    for key in invalid:
        try:
            module.extension_id_from_key(key)
        except ValueError:
            continue
        raise AssertionError("Invalid public-key representation was accepted")
    print("PASS five invalid public-key representations fail before release construction")
    assert "MIT License" in (root / "LICENSE").read_text(encoding="utf-8")
    expected_sources = {"README.md", "LICENSE", "global.json", "NuGet.Config", "package.json", "package-lock.json", ".github/workflows/ci.yml"}
    assert expected_sources.issubset(set(module.ROOT_SOURCE_FILES))
    for file in expected_sources:
        assert (root / file).is_file(), "Missing public build/source document: " + file
    print("PASS source release allowlist includes MIT license, build configuration, dependency lock and CI")
    print("3/3 release-policy groups passed without building, installing or publishing.")


if __name__ == "__main__":
    main()
