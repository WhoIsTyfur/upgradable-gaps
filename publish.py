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
USER_AGENT = "TinyGecko920/upgradable-gaps publish.py"
MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://minecraft.curseforge.com/api"
HANGAR_API = "https://hangar.papermc.io/api/v1"
# CurseForge rejects mod files without an environment. Server-side, but singleplayer
# runs the server inside the client, so it fits both.
CURSEFORGE_ENVIRONMENTS = ["Client", "Server"]


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
        "project_id": os.environ.get("MODRINTH_PROJECT_ID", "<MODRINTH_PROJECT_ID>"),
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
    result = request(f"{MODRINTH_API}/version", {"Authorization": os.environ["MODRINTH_TOKEN"]}, body, content_type)
    print("  modrinth: version", result["id"])


_curseforge_versions: dict[str, int] | None = None


def curseforge_version_ids(names: list[str]) -> list[int]:
    global _curseforge_versions
    if _curseforge_versions is None:
        headers = {"X-Api-Token": os.environ["CURSEFORGE_TOKEN"]}
        types = request(f"{CURSEFORGE_API}/game/version-types", headers)
        # Loaders and environments are game versions of their own types on CurseForge.
        wanted = {t["id"] for t in types if t["slug"].startswith(("minecraft-", "modloader", "environment"))}
        versions = request(f"{CURSEFORGE_API}/game/versions", headers)
        _curseforge_versions = {v["name"]: v["id"] for v in versions if v["gameVersionTypeID"] in wanted}
    missing = [n for n in names if n not in _curseforge_versions]
    if missing:
        raise RuntimeError(f"CurseForge has no game version for: {', '.join(missing)}")
    return [_curseforge_versions[n] for n in names]


def curseforge(entry: dict, changelog: str, dry_run: bool) -> None:
    if entry.get("plugin") or not entry["curseforge_loaders"]:
        return
    names = entry["game_versions"] + entry["curseforge_loaders"] + CURSEFORGE_ENVIRONMENTS
    metadata = {
        "changelog": changelog,
        "changelogType": "markdown",
        "displayName": display_name(entry),
        "releaseType": "release",
    }
    if dry_run:
        print("  curseforge:", json.dumps({**metadata, "gameVersions": names}))
        return
    metadata["gameVersions"] = curseforge_version_ids(names)
    body, content_type = multipart({"metadata": json.dumps(metadata)}, {"file": DIST / entry["file"]})
    project = os.environ["CURSEFORGE_PROJECT_ID"]
    result = request(
        f"{CURSEFORGE_API}/projects/{project}/upload-file", {"X-Api-Token": os.environ["CURSEFORGE_TOKEN"]}, body, content_type
    )
    print("  curseforge: file", result["id"])


_hangar_jwt: str | None = None


def hangar(entry: dict, changelog: str, dry_run: bool) -> None:
    global _hangar_jwt
    if not entry.get("plugin"):
        return
    versions = entry["game_versions"]
    upload = {
        "version": entry["version_number"],
        "channel": "Release",
        "description": changelog,
        "platformDependencies": {"PAPER": [f"{versions[0]}-{versions[-1]}"]},
        "pluginDependencies": {},
        "files": [{"platforms": ["PAPER"]}],
    }
    if dry_run:
        print("  hangar:", json.dumps(upload))
        return
    if _hangar_jwt is None:
        query = urllib.parse.urlencode({"apiKey": os.environ["HANGAR_API_KEY"]})
        _hangar_jwt = request(f"{HANGAR_API}/authenticate?{query}", {}, method="POST")["token"]
    body, content_type = multipart({"versionUpload": json.dumps(upload)}, {"files": DIST / entry["file"]})
    project = urllib.parse.quote(os.environ["HANGAR_PROJECT"])
    result = request(f"{HANGAR_API}/projects/{project}/upload", {"Authorization": f"HangarAuth {_hangar_jwt}"}, body, content_type)
    print("  hangar:", result.get("url", result))


PLATFORMS = {
    modrinth: ("MODRINTH_TOKEN", "MODRINTH_PROJECT_ID"),
    curseforge: ("CURSEFORGE_TOKEN", "CURSEFORGE_PROJECT_ID"),
    hangar: ("HANGAR_API_KEY", "HANGAR_PROJECT"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print what would be uploaded")
    args = parser.parse_args()

    manifest = json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))
    uploads = [p for p, needs in PLATFORMS.items() if args.dry_run or all(os.environ.get(v) for v in needs)]
    if not uploads:
        print("no platform credentials set; nothing to do", file=sys.stderr)
        return 1

    for entry in manifest:
        mod_version = entry["version_number"].split("+", 1)[0]
        print(entry["file"])
        for upload in uploads:
            upload(entry, changelog_for(mod_version), args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
