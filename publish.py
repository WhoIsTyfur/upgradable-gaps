#!/usr/bin/env python3
# Copyright (c) 2026 Tyler Fursman
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Upload the jars listed in dist/manifest.json.

Each platform runs only when its variables are set:
  Modrinth         MODRINTH_TOKEN, MODRINTH_PROJECT_ID     every jar
  CurseForge       CURSEFORGE_TOKEN, CURSEFORGE_PROJECT_ID mod jars
  Hangar           HANGAR_API_KEY, HANGAR_PROJECT          the plugin
The plugin goes to SpigotMC and to CurseForge's Bukkit Plugins by hand: SpigotMC
has no upload API, and CurseForge's plugin API (dev.bukkit.org) only takes a
Twitch login.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
USER_AGENT = "WhoIsTyfur/upgradable-gaps publish.py"
MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://minecraft.curseforge.com/api"
HANGAR_API = "https://hangar.papermc.io/api/v1"
# CurseForge rejects mod files without an environment. Server-side, but singleplayer
# runs the server inside the client, so it fits both.
CURSEFORGE_ENVIRONMENTS = ["Client", "Server"]
# Hangar's list of Paper versions starts at 1.8.
HANGAR_OLDEST = "1.8"


def env(name: str, default: str = "") -> str:
    # A secret pasted with a trailing newline keeps it, and Hangar rejects such a key.
    return os.environ.get(name, default).strip()


def multipart(fields: dict[str, str], files: dict[str, pathlib.Path]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n'
            f"Content-Type: application/json\r\n\r\n{value}\r\n".encode()
        )
    for name, path in files.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: application/java-archive\r\n\r\n".encode()
            + path.read_bytes()
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def request(url: str, headers: dict[str, str], body: bytes | None = None, content_type: str | None = None, method: str | None = None):
    headers = {"User-Agent": USER_AGENT, **headers}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"{url}: HTTP {err.code}: {err.read().decode(errors='replace')}") from None


def changelog_for(version: str) -> str:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        return ""
    match = re.search(rf"^## {re.escape(version)}\b.*?\n(.*?)(?=^## |\Z)", path.read_text(encoding="utf-8"), re.S | re.M)
    return match.group(1).strip() if match else ""


def display_name(entry: dict) -> str:
    return f"Upgradable Gaps {entry['version_number']}"


def modrinth(entry: dict, changelog: str, dry_run: bool) -> None:
    data = {
        "project_id": env("MODRINTH_PROJECT_ID", "<MODRINTH_PROJECT_ID>"),
        "name": display_name(entry),
        "version_number": entry["version_number"],
        "changelog": changelog,
        "dependencies": [],
        "game_versions": entry["game_versions"],
        "version_type": "release",
        "loaders": entry["loaders"],
        "featured": False,
        "file_parts": ["file"],
        "primary_file": "file",
    }
    if dry_run:
        print("  modrinth:", json.dumps(data))
        return
    body, content_type = multipart({"data": json.dumps(data)}, {"file": DIST / entry["file"]})
    result = request(f"{MODRINTH_API}/version", {"Authorization": env("MODRINTH_TOKEN")}, body, content_type)
    print("  modrinth: version", result["id"])


_curseforge_versions: dict[str, int] | None = None


def curseforge_versions() -> dict[str, int]:
    global _curseforge_versions
    if _curseforge_versions is None:
        headers = {"X-Api-Token": env("CURSEFORGE_TOKEN")}
        types = request(f"{CURSEFORGE_API}/game/version-types", headers)
        # Loaders and environments are game versions of their own types on CurseForge.
        wanted = {t["id"] for t in types if t["slug"].startswith(("minecraft-", "modloader", "environment"))}
        versions = request(f"{CURSEFORGE_API}/game/versions", headers)
        _curseforge_versions = {v["name"]: v["id"] for v in versions if v["gameVersionTypeID"] in wanted}
    return _curseforge_versions


def check_curseforge(manifest: list[dict]) -> None:
    """Resolve every name before anything uploads. Minecraft versions CurseForge lacks
    are left off, and a jar with none of its versions there is skipped."""
    known = curseforge_versions()
    tags = {n for e in manifest for n in e["curseforge_loaders"]} | set(CURSEFORGE_ENVIRONMENTS)
    missing = sorted(n for n in tags if n not in known)
    if missing:
        raise RuntimeError(f"CurseForge has no game version for: {', '.join(missing)}")
    for entry in manifest:
        if entry.get("plugin") or not entry["curseforge_loaders"]:
            continue
        entry["curseforge_game_versions"] = [v for v in entry["game_versions"] if v in known]
        dropped = [v for v in entry["game_versions"] if v not in known]
        if dropped:
            what = "goes up without them" if entry["curseforge_game_versions"] else "is skipped there"
            print(f"warning: CurseForge lacks {', '.join(dropped)}; {entry['file']} {what}")


def curseforge(entry: dict, changelog: str, dry_run: bool) -> None:
    if entry.get("plugin") or not entry["curseforge_loaders"]:
        return
    versions = entry.get("curseforge_game_versions", entry["game_versions"])
    if not versions:
        print("  curseforge: skipped, it has none of these Minecraft versions")
        return
    names = versions + entry["curseforge_loaders"] + CURSEFORGE_ENVIRONMENTS
    metadata = {
        "changelog": changelog,
        "changelogType": "markdown",
        "displayName": display_name(entry),
        "releaseType": "release",
    }
    if dry_run:
        print("  curseforge:", json.dumps({**metadata, "gameVersions": names}))
        return
    metadata["gameVersions"] = [curseforge_versions()[n] for n in names]
    body, content_type = multipart({"metadata": json.dumps(metadata)}, {"file": DIST / entry["file"]})
    project = env("CURSEFORGE_PROJECT_ID")
    result = request(
        f"{CURSEFORGE_API}/projects/{project}/upload-file", {"X-Api-Token": env("CURSEFORGE_TOKEN")}, body, content_type
    )
    print("  curseforge: file", result["id"])


_hangar_jwt: str | None = None


def hangar_jwt() -> str:
    global _hangar_jwt
    if _hangar_jwt is None:
        key = env("HANGAR_API_KEY")
        query = urllib.parse.urlencode({"apiKey": key})
        try:
            _hangar_jwt = request(f"{HANGAR_API}/authenticate?{query}", {}, method="POST")["token"]
        except RuntimeError as err:
            # Describe the saved key's shape without printing the secret itself.
            shape = f"{len(key)} characters in {len(key.split('.'))} dot-separated part(s)"
            raise RuntimeError(f"{err}\nHANGAR_API_KEY is {shape}; a Hangar key is two long codes joined by one dot") from None
    return _hangar_jwt


def hangar(entry: dict, changelog: str, dry_run: bool) -> None:
    if not entry.get("plugin"):
        return
    upload = {
        "version": entry["version_number"],
        "channel": "Release",
        "description": changelog,
        "platformDependencies": {"PAPER": [f"{HANGAR_OLDEST}-{entry['game_versions'][-1]}"]},
        "pluginDependencies": {},
        "files": [{"platforms": ["PAPER"]}],
    }
    if dry_run:
        print("  hangar:", json.dumps(upload))
        return
    body, content_type = multipart({"versionUpload": json.dumps(upload)}, {"files": DIST / entry["file"]})
    project = urllib.parse.quote(env("HANGAR_PROJECT"))
    result = request(f"{HANGAR_API}/projects/{project}/upload", {"Authorization": f"HangarAuth {hangar_jwt()}"}, body, content_type)
    print("  hangar:", result.get("url", result))


# Strictest first: a rejection should stop the run before Modrinth, which takes
# anything, holds a copy someone has to delete by hand.
PLATFORMS = {
    hangar: ("HANGAR_API_KEY", "HANGAR_PROJECT"),
    curseforge: ("CURSEFORGE_TOKEN", "CURSEFORGE_PROJECT_ID"),
    modrinth: ("MODRINTH_TOKEN", "MODRINTH_PROJECT_ID"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print what would be uploaded")
    args = parser.parse_args()

    manifest = json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))
    uploads = [p for p, needs in PLATFORMS.items() if args.dry_run or all(env(v) for v in needs)]
    if not uploads:
        print("no platform credentials set; nothing to do", file=sys.stderr)
        return 1

    # The plugin first too, so Hangar (its only extra platform) is tried early.
    manifest.sort(key=lambda e: not e.get("plugin"))
    if not args.dry_run:
        if curseforge in uploads:
            check_curseforge(manifest)
        if hangar in uploads:
            hangar_jwt()

    for entry in manifest:
        mod_version = entry["version_number"].split("+", 1)[0]
        print(entry["file"])
        for upload in uploads:
            upload(entry, changelog_for(mod_version), args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
