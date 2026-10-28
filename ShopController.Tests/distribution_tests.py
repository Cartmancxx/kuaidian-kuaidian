"""Inspect release archives without extracting, installing, or executing software."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import stat
import struct
import zipfile
from pathlib import Path, PurePosixPath


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def safe_names(archive):
    names = archive.namelist()
    require(len(names) == len(set(names)), "No duplicate ZIP entries")
    for name in names:
        path = PurePosixPath(name)
        require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts and
                "\\" not in name and ":" not in name and not any(ord(c) < 32 for c in name), "Unsafe ZIP member: " + name)
        require(not stat.S_ISLNK(archive.getinfo(name).external_attr >> 16), "No symlink ZIP entry: " + name)
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("release_directory", type=Path)
    args = parser.parse_args()
    root = args.release_directory.resolve()
    release = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
    channel = release.get("channel", "store")
    require(channel in {"store", "github"}, "Explicit supported release channel")
    product = Path(__file__).resolve().parents[1] / "ShopController"
    source_manifest = json.loads((product / "extension/manifest.json").read_text(encoding="utf-8-sig"))
    public_key = base64.b64decode(source_manifest["key"], validate=True)
    github_id = "".join(chr(ord("a") + int(nibble, 16)) for nibble in hashlib.sha256(public_key).hexdigest()[:32])
    passed = 0

    def done(message):
        nonlocal passed
        passed += 1
        print("PASS ", message)

    extension = root / "ShopController-extension-1.0.0.zip"
    with zipfile.ZipFile(extension) as archive:
        names = safe_names(archive)
        require("manifest.json" in names, "Store ZIP must have manifest.json at archive root")
        manifest = json.loads(archive.read("manifest.json"))
        require(manifest["manifest_version"] == 3 and manifest["version"] == "1.0.0", "Manifest version")
        require("key" not in manifest, "Store ZIP omits the fixed unpacked public identity key")
        require(sorted(manifest["permissions"]) == ["nativeMessaging", "storage"], "Minimal permissions")
        require(not manifest.get("host_permissions") and not manifest.get("content_scripts"), "No broad site access")
        forbidden = ("demo.js", "config.json", "host-identity.json")
        require(not any(PurePosixPath(name).name in forbidden or name.lower().endswith((".exe", ".dll", ".pdb", ".pyc")) for name in names), "Store ZIP includes only extension assets")
        require("export const isDemo = false" in archive.read("api.js").decode(), "Production demo path disabled")
        for icon, name in manifest.get("icons", {}).items():
            data = archive.read(name)
            require(data.startswith(b"\x89PNG\r\n\x1a\n"), "Store icon should be PNG")
            width, height = struct.unpack(">II", data[16:24])
            require(width == height == int(icon), "Icon dimensions match manifest")
        require("128" in manifest.get("icons", {}), "Required 128px listing icon supplied")
        current_manifest = dict(source_manifest)
        current_manifest.pop("key", None)
        require(manifest == current_manifest, "Store manifest matches the reviewed current source")
        for name in names:
            if name.endswith("/") or name in {"manifest.json", "release-info.json"}:
                continue
            current = product / "extension" / name
            require(current.is_file() and current.read_bytes() == archive.read(name), "Store payload matches reviewed current source: " + name)
        release_info = json.loads(archive.read("release-info.json"))
        metadata = json.loads((product / "release-config.json").read_text(encoding="utf-8-sig"))
        for field in ("productName", "publisherName", "supportEmail", "privacyPolicyUrl", "downloadPageUrl"):
            require(release_info.get(field) == metadata.get(field), "Packaged public metadata matches release configuration: " + field)
        done("store ZIP has root MV3 manifest, production-only assets, minimal permissions, valid icons")

    if channel == "github":
        unpacked = root / "ShopController-extension-unpacked-1.0.0.zip"
        with zipfile.ZipFile(unpacked) as archive, zipfile.ZipFile(extension) as store:
            names = safe_names(archive)
            require(set(names) == set(store.namelist()), "GitHub and store extension packages have the same production assets")
            require(json.loads(archive.read("manifest.json")) == source_manifest, "GitHub manifest retains the reviewed fixed public key")
            for name in names:
                if name != "manifest.json":
                    require(archive.read(name) == store.read(name), "Only the manifest identity differs between extension channels: " + name)
        require(release.get("extensionId") == github_id and release.get("githubExtensionId") == github_id, "GitHub release identity is independently derived from the manifest public key")
        require(release.get("identitySource") == "manifest-key", "GitHub identity source is explicit")
        store_id = release.get("storeExtensionId")
        require(store_id is None or isinstance(store_id, str) and len(store_id) == 32 and all("a" <= c <= "p" for c in store_id), "Unknown store identity remains null and any supplied identity is valid")
        done("GitHub unpacked extension keeps its fixed public identity and identical production assets")

    for rid, cpu in [("win-x64", None), ("osx-arm64", 0x0100000C), ("osx-x64", 0x01000007)]:
        with zipfile.ZipFile(root / f"ShopController-helper-1.0.0-{rid}.zip") as archive:
            names = safe_names(archive)
            prefix = f"ShopController-{rid}/"
            require(all(name.startswith(prefix) for name in names), "Consistent helper top-level directory")
            config = json.loads(archive.read(prefix + "release-config.json"))
            identifier = config.get("extensionId")
            require(identifier is None or len(identifier) == 32 and all("a" <= c <= "p" for c in identifier), "Valid optional store binding")
            require(config.get("targetFramework") == "net10.0", "Helper uses the supported release target framework")
            require(config.get("bindingStatus") == ("bound" if identifier else "unbound"), "Binding status is truthful")
            require(config.get("signed") is False and config.get("notarized") is False, "Cross-built packages do not invent signature status")
            if channel == "github":
                require(config.get("channel") == "github" and config.get("identitySource") == "manifest-key", "Helper declares the GitHub identity channel")
                require(identifier == github_id and config.get("bindingStatus") == "bound", "GitHub helper is bound to the independently computed unpacked extension ID")
            require(not any(PurePosixPath(name).name in {"config.json", "Cookies", "Login Data", "host-identity.json"} for name in names), "No personal browser/configuration data or preinstalled identity")
            executable = prefix + "host/ShopController.Host" + (".exe" if cpu is None else "")
            data = archive.read(executable)
            if cpu is None:
                require(data.startswith(b"MZ"), "Windows apphost must be a PE image")
                pe_offset = struct.unpack("<I", data[60:64])[0]
                require(data[pe_offset:pe_offset + 4] == b"PE\0\0" and struct.unpack("<H", data[pe_offset + 4:pe_offset + 6])[0] == 0x8664, "Windows apphost must be x64")
                require(prefix + "Install.ps1" in names and prefix + "Install.cmd" in names, "Windows installer present")
            else:
                require(data[:4] == b"\xcf\xfa\xed\xfe", "Mac apphost must be a little-endian 64-bit Mach-O")
                require(struct.unpack("<I", data[4:8])[0] == cpu, "Mach-O CPU matches archive architecture")
                for name in names:
                    if name == executable or name.endswith((".sh", ".command", ".dylib")):
                        require(archive.getinfo(name).external_attr >> 16 & 0o111, "Mac executable permissions retained: " + name)
                require(any(name.endswith("Install.command") for name in names), "Mac installation entry point present")
                require(config.get("minimumMacOS") == "15.0", "Current runtime OS support floor is explicit")
                for name in names:
                    if name.endswith((".sh", ".command")):
                        require(b"\r\n" not in archive.read(name), "Mac shell scripts use Unix line endings")
            require(prefix + "runtime-notices/LICENSE.txt" in names and prefix + "runtime-notices/ThirdPartyNotices.txt" in names, "Runtime license attribution supplied")
            done(f"{rid} helper archive has correct binary architecture, installation files, permissions and no private configuration")

    source_archives = list(root.glob("*source*.zip"))
    require(len(source_archives) == 1, "Exactly one source archive")
    with zipfile.ZipFile(source_archives[0]) as archive:
        names = safe_names(archive)
        for name in names:
            parts = PurePosixPath(name).parts
            require(not any(part in {"bin", "obj", "__pycache__", ".git", "verification"} for part in parts), "Clean source archive: " + name)
            require(not name.endswith((".pyc", ".pdb")), "No local build artifacts")
            require(parts[0] in {"ShopController", "ShopController.Core", "ShopController.Tests", ".github", "docs", "README.md", "LICENSE", ".gitignore", ".gitattributes", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md", "global.json", "NuGet.Config", "package.json", "package-lock.json", "Directory.Build.props", "Directory.Build.targets"}, "Only explicitly allowed public project sources are included")
        if channel == "github":
            require("LICENSE" in names and "README.md" in names, "Open-source release includes root license and reproduction instructions")
            require(any(name.startswith(".github/workflows/") for name in names), "Open-source release includes its CI workflow")
        done("source archive excludes build caches, personal verification captures and unrelated project")

    hash_lines = (root / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    seen = set()
    for line in hash_lines:
        digest, name = line.split("  ", 1)
        require(name not in seen and Path(name).name == name, "Hash list paths are unique filenames")
        seen.add(name)
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, "ZIP digest matches " + name)
    require(seen == {file.name for file in root.glob("*.zip")}, "All release ZIPs covered by checksums")
    require(release.get("storeApproval") == "not-submitted" and release.get("signatureStatus") == "unsigned", "Release metadata does not claim unperformed submission/signing")
    if channel == "github":
        require(isinstance(release.get("pendingReleaseRequirements"), list), "GitHub readiness requirements use an explicit list")
        require(release.get("warnings"), "Unsigned and untested platform status remains disclosed even when GitHub requirements are complete")
    else:
        require(release.get("pendingReleaseRequirements"), "Outstanding store release checks are explicit")
    done("all ZIP checksums verify and release metadata discloses remaining public-release gates")

    print(f"\n{passed}/{passed} distribution archive groups passed. No files were installed or executed.")


if __name__ == "__main__":
    main()
