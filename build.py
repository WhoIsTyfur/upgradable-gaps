#!/usr/bin/env python3
# Copyright (c) 2026 Tyler Fursman
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Build every jar, copy the release ones to dist/ and describe them in dist/manifest.json.

Each Gradle build runs on a Temurin JDK fetched by the test harness, so nothing
needs installing first. Targets whose gradle.properties say publish=false are
built but left out of dist/.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT / "test"))

import mctest  # noqa: E402

# Build folder -> JDK Gradle runs on. Gradle 8.14 in forge-legacy predates JDK 25.
BUILDS = {"modern": 25, "ornithe": 25, "forge-legacy": 21, "bukkit": 25}

# Modrinth loader tags, and the CurseForge loaders a jar is listed under (none: not uploaded there).
LOADERS = {
    "fabric": (["fabric", "quilt"], ["Fabric", "Quilt"]),
    "forge": (["forge"], ["Forge"]),
    "neoforge": (["neoforge"], ["NeoForge"]),
    # CurseForge has no Ornithe tag, and the jars do not run on its Fabric (Legacy Fabric) either.
    "ornithe": (["ornithe"], []),
}
PLUGIN_LOADERS = ["bukkit", "spigot", "paper", "purpur", "folia"]


def read_properties(path: pathlib.Path) -> dict[str, str]:
    props = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def mod_version() -> str:
    versions = {read_properties(ROOT / build / "gradle.properties")["mod_version"] for build in BUILDS}
    if len(versions) != 1:
        raise SystemExit(f"mod_version differs between builds: {sorted(versions)}")
    return versions.pop()


def gradle(build: str, jdk: int) -> None:
    java = mctest.java_executable(jdk)
    env = dict(os.environ, JAVA_HOME=str(java.parent.parent))
    wrapper = ROOT / build / ("gradlew.bat" if os.name == "nt" else "gradlew")
    print(f"== {build} (JDK {jdk})", flush=True)
    subprocess.run([str(wrapper), "build", "--no-daemon", "-q"], cwd=ROOT / build, env=env, check=True)


def release_versions(first: str, last: str) -> list[str]:
    """Every release from first to last, oldest first."""
    releases = [v["id"] for v in reversed(mctest.cached_json(mctest.VERSION_MANIFEST)["versions"]) if v["type"] == "release"]
    return releases[releases.index(first) : releases.index(last) + 1]


def release_jar(libs: pathlib.Path) -> pathlib.Path:
    jars = [j for j in libs.glob("*.jar") if not j.name.endswith(("-sources.jar", "-dev.jar"))]
    if len(jars) != 1:
        raise SystemExit(f"expected one release jar in {libs}, found {[j.name for j in jars]}")
    return jars[0]


def mod_entries() -> list[dict]:
    entries = []
    for build in ("modern", "ornithe", "forge-legacy"):
        default_loader = {"ornithe": "ornithe", "forge-legacy": "forge"}.get(build)
        for folder in sorted((ROOT / build / "targets").iterdir()):
            props = read_properties(folder / "gradle.properties")
            if props.get("publish") == "false":
                print(f"   skipping {folder.name} (publish=false)")
                continue
            loader = props.get("loom.platform", default_loader)
            modrinth, curseforge = LOADERS[loader]
            jar = release_jar(folder / "build" / "libs")
            entries.append(
                {
                    "file": jar.name,
                    "source": str(jar),
                    "game_versions": props["game_versions"].split(","),
                    "loaders": modrinth,
                    "curseforge_loaders": curseforge,
                }
            )
    return entries


def plugin_entry() -> dict:
    props = read_properties(ROOT / "bukkit" / "gradle.properties")
    first, last = props["game_versions"].split("..")
    jar = release_jar(ROOT / "bukkit" / "build" / "libs")
    return {
        "file": jar.name,
        "source": str(jar),
        "game_versions": release_versions(first, last),
        "loaders": PLUGIN_LOADERS,
        "curseforge_loaders": [],
        "plugin": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-gradle", action="store_true", help="collect jars from an earlier build")
    args = parser.parse_args()

    version = mod_version()
    if not args.skip_gradle:
        for build, jdk in BUILDS.items():
            gradle(build, jdk)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    manifest = []
    for entry in mod_entries() + [plugin_entry()]:
        shutil.copy2(entry.pop("source"), DIST / entry["file"])
        entry["version_number"] = entry["file"].removeprefix("upgradable-gaps-").removesuffix(".jar")
        manifest.append(entry)
        print(f"{entry['file']}  ({entry['game_versions'][0]} - {entry['game_versions'][-1]})")
    if not all(e["version_number"].startswith(version + "+") for e in manifest):
        raise SystemExit("a jar's version does not start with mod_version")
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(manifest)} files for {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
