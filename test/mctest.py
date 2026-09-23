#!/usr/bin/env python3
# Copyright (c) 2026 Tyler Fursman
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Provision real Minecraft servers (vanilla, Fabric, Forge, NeoForge) and drive a bot against them."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import socket
import subprocess
import tarfile
import threading
import time
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN = ROOT / "run"
BOT = pathlib.Path(__file__).resolve().parent / "bot"
CACHE = pathlib.Path(os.environ.get("MCTEST_CACHE", pathlib.Path.home() / ".cache" / "mctest"))

USER_AGENT = "mctest/1.0 (+https://github.com/TinyGecko920/upgradable-gaps)"
VERSION_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ADOPTIUM = (
    "https://api.adoptium.net/v3/assets/latest/{feature}/hotspot"
    "?architecture=x64&image_type=jdk&os={os}&vendor=eclipse"
)
ADOPTIUM_RELEASE = (
    "https://api.adoptium.net/v3/assets/release_name/eclipse/{release}"
    "?architecture=x64&heap_size=normal&image_type=jdk&os={os}&project=jdk"
)
FABRIC_META = "https://meta.fabricmc.net/v2"
FORGE_MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge"
FORGE_PROMOTIONS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
FORGE_LIBRARIES = "https://maven.minecraftforge.net"
MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
# Forge's own fmllibs host is gone; Prism Launcher mirrors it (Tyler approved using it on 2026-09-22).
FMLLIBS = "https://files.prismlauncher.org/fmllibs"
# What Forge 1.3.2-1.5.2 fetch into lib/ at start, with the SHA-1 FML itself checks.
FML_LIBRARIES = {
    "argo-2.25.jar": (f"{MAVEN_CENTRAL}/net/sourceforge/argo/argo/2.25/argo-2.25.jar", "bb672829fde76cb163004752b86b0484bd0a7f4b"),
    "guava-12.0.1.jar": (f"{MAVEN_CENTRAL}/com/google/guava/guava/12.0.1/guava-12.0.1.jar", "b8e78b9af7bf45900e14c6f958486b6ca682195f"),
    # FML's own build; Maven Central's asm-all 4.0 has a different hash.
    "asm-all-4.0.jar": (f"{FMLLIBS}/asm-all-4.0.jar", "98308890597acb64047f7e896638e0d98753ae82"),
    "bcprov-jdk15on-147.jar": (
        f"{MAVEN_CENTRAL}/org/bouncycastle/bcprov-jdk15on/1.47/bcprov-jdk15on-1.47.jar",
        "b6f5d9926b0afbde9f4dbe3db88c5247be7794bb",
    ),
    "argo-small-3.2.jar": (f"{FORGE_LIBRARIES}/net/sourceforge/argo/argo/3.2-small/argo-3.2-small.jar", "58912ea2858d168c50781f956fa5b59f0f7c6b51"),
    "guava-14.0-rc3.jar": (f"{FORGE_LIBRARIES}/com/google/guava/guava/14.0-rc3/guava-14.0-rc3.jar", "931ae21fa8014c3ce686aaa621eae565fefb1a6a"),
    "asm-all-4.1.jar": (f"{FORGE_LIBRARIES}/org/ow2/asm/asm-all/4.1/asm-all-4.1.jar", "054986e962b88d8660ae4566475658469595ef58"),
    "bcprov-jdk15on-148.jar": (
        f"{FORGE_LIBRARIES}/org/bouncycastle/bcprov-jdk15on/148/bcprov-jdk15on-148.jar",
        "960dea7c9181ba0b17e8bab0c06a43f0a5f04e65",
    ),
    "scala-library.jar": (
        f"{FORGE_LIBRARIES}/org/scala-lang/scala-library/2.10.0-custom/scala-library-2.10.0-custom.jar",
        "458d046151ad179c85429ed7420ffb1eaf6ddf85",
    ),
    "deobfuscation_data_1.5.zip": (f"{FMLLIBS}/deobfuscation_data_1.5.zip", "5f7c142d53776f16304c0bbe10542014abad6af8"),
    "deobfuscation_data_1.5.1.zip": (f"{FMLLIBS}/deobfuscation_data_1.5.1.zip", "22e221a0d89516c1f721d6cab056a7e37471d0a6"),
    "deobfuscation_data_1.5.2.zip": (f"{FMLLIBS}/deobfuscation_data_1.5.2.zip", "446e55cd986582c70fcf12cb27bc00114c5adfd9"),
}
NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
ORNITHE_INSTALLER = (
    "https://maven.ornithemc.net/releases/net/ornithemc/ornithe-installer/0.16.0/ornithe-installer-0.16.0.jar",
    "ca35f1233bd5c44c07df297d4173aabea0f5c3f5b1d138bce9e6938547d7ae8a",
)
QUILT_META = "https://meta.quiltmc.org/v3"
# Pinned: Quilt's meta lists stale hashes for this installer; these match its Maven checksums.
QUILT_INSTALLER = (
    "https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/0.15.1/quilt-installer-0.15.1.jar",
    "0a229138caa1b87fd8f5622038410696f98bb85871a279640e7002404c4d0dc2",
)
FILL = "https://fill.papermc.io/v3/projects"
PURPUR_API = "https://api.purpurmc.org/v2/purpur"
BUILDTOOLS = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
# Old Paper and Spigot builds stall 20 seconds when they think they are outdated.
SKIP_OUTDATED_WAIT = "-DIReallyKnowWhatIAmDoingISwear=true"
VIAPROXY = (
    "https://github.com/ViaVersion/ViaProxy/releases/download/v3.4.13/ViaProxy-3.4.13.jar",
    "4bbb6a6b9d3dd6a2028773ed44b97a98751e4a48e416aaad4bf6d9c860083be9",
)
BOT_NAME = "tester"
# Each scenario logs in as its own player, so none needs /clear (added in 1.4.2).
BOT_NAMES = [f"{BOT_NAME}{i}" for i in range(8)]

# mineflayer 4.39.0 has no data for these; they share a protocol with the listed version.
BOT_ALIASES = {
    "1.9.3": "1.9.4",
    "1.11.1": "1.11.2",
    "1.19.1": "1.19.2",
    "1.21.2": "1.21.3",
    "1.21.7": "1.21.8",
    "26.1.1": "26.1",
    "26.1.2": "26.1",
}

# No same-protocol data at all: (client version the bot uses, ViaProxy target).
VIA_ROUTES = {
    **{v: ("1.8.8", "1.3.1-1.3.2") for v in ("1.3.1", "1.3.2")},
    "1.4.2": ("1.8.8", "1.4.2"),
    **{v: ("1.8.8", "1.4.4-1.4.5") for v in ("1.4.4", "1.4.5")},
    **{v: ("1.8.8", "1.4.6-1.4.7") for v in ("1.4.6", "1.4.7")},
    "1.5.1": ("1.8.8", "1.5-1.5.1"),
    "1.5.2": ("1.8.8", "1.5.2"),
    "1.6.1": ("1.8.8", "1.6.1"),
    "1.6.2": ("1.8.8", "1.6.2"),
    "1.6.4": ("1.8.8", "1.6.4"),
    **{v: ("1.8.8", "1.7.2-1.7.5") for v in ("1.7.2", "1.7.3", "1.7.4", "1.7.5")},
    **{v: ("1.8.8", "1.7.6-1.7.10") for v in ("1.7.6", "1.7.7", "1.7.8", "1.7.9", "1.7.10")},
    "1.9.1": ("1.9.4", "1.9.1"),
    "1.13.1": ("1.13.2", "1.13.1"),
    "1.14.2": ("1.14.4", "1.14.2"),
    "26.2": ("26.1", "26.2"),
    "26.3": ("26.1", "26.3"),
}

# ViaProxy 3.4.13 turns the bot's routine movement packets into ones these reject.
NO_MOVEMENT = {"26.3"}

_print_lock = threading.Lock()
_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def download(
    url: str, dest: pathlib.Path, *, sha1: str | None = None, sha256: str | None = None, md5: str | None = None
) -> pathlib.Path:
    with lock_for(str(dest)):
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = http_get(url)
        if md5 and hashlib.md5(data).hexdigest() != md5:
            raise RuntimeError(f"md5 mismatch for {url}")
        if sha1 and hashlib.sha1(data).hexdigest() != sha1:
            raise RuntimeError(f"sha1 mismatch for {url}")
        if sha256 and hashlib.sha256(data).hexdigest() != sha256:
            raise RuntimeError(f"sha256 mismatch for {url}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return dest


def java_executable(major: int, release: str | None = None) -> pathlib.Path:
    """Latest JDK of a major version, or an exact Adoptium release such as jdk8u312-b07."""
    home = CACHE / "jdk" / (release or str(major))
    exe_name = "java.exe" if os.name == "nt" else "java"
    with lock_for(str(home)):
        found = sorted(home.glob(f"*/bin/{exe_name}"))
        if found:
            return found[0]
        os_name = {"Windows": "windows", "Linux": "linux", "Darwin": "mac"}[platform.system()]
        if release:
            info = json.loads(http_get(ADOPTIUM_RELEASE.format(release=release, os=os_name)))
            package = info["binaries"][0]["package"]
        else:
            package = json.loads(http_get(ADOPTIUM.format(feature=major, os=os_name)))[0]["binary"]["package"]
        archive = download(package["link"], CACHE / "downloads" / package["name"], sha256=package["checksum"])
        log(f"extracting JDK {release or major}")
        # Extract beside the target and rename, so a half-written JDK is never picked up.
        staging = home.with_name(home.name + ".extracting")
        shutil.rmtree(staging, ignore_errors=True)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(staging)
        else:
            with tarfile.open(archive) as tf:
                tf.extractall(staging, filter="data")
            for java in staging.glob("*/bin/java"):
                java.chmod(0o755)
        shutil.rmtree(home, ignore_errors=True)
        staging.rename(home)
        return sorted(home.glob(f"*/bin/{exe_name}"))[0]


_json_cache: dict[str, object] = {}


def cached_json(url: str):
    with lock_for("json:" + url):
        if url not in _json_cache:
            _json_cache[url] = json.loads(http_get(url))
        return _json_cache[url]


def cached_text(url: str) -> str:
    with lock_for("text:" + url):
        if url not in _json_cache:
            _json_cache[url] = http_get(url).decode("utf-8")
        return _json_cache[url]


def version_json(version: str) -> dict:
    manifest = cached_json(VERSION_MANIFEST)
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if entry is None:
        raise RuntimeError(f"unknown Minecraft version {version}")
    path = download(entry["url"], CACHE / "versions" / f"{version}.json", sha1=entry["sha1"])
    return json.loads(path.read_text(encoding="utf-8"))


def java_major(version: str) -> int:
    return version_json(version).get("javaVersion", {}).get("majorVersion", 8)


def vanilla_jar(version: str) -> pathlib.Path:
    server = version_json(version)["downloads"]["server"]
    return download(server["url"], CACHE / "vanilla" / version / "server.jar", sha1=server["sha1"])


def offline_uuid(name: str) -> str:
    # Same as Java's UUID.nameUUIDFromBytes("OfflinePlayer:" + name).
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(digest)))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def link(source: pathlib.Path, target: pathlib.Path) -> None:
    """Share a cached file or folder with an instance without copying it."""
    if source.is_dir():
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(source), str(target))
        else:
            target.symlink_to(source, target_is_directory=True)
        return
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


@dataclass
class Server:
    """A launchable server: `java <jvm args> <args>` run inside an instance folder."""

    java_major: int
    args: list[str]
    files: dict[str, pathlib.Path] = field(default_factory=dict)
    content_folder: str = "mods"
    # Files to copy rather than link into the instance.
    copies: tuple[str, ...] = ()
    # An exact JDK release, for servers that break on newer updates of their Java version.
    java_release: str | None = None


def vanilla(mc: str) -> Server:
    return Server(java_major(mc), ["-jar", str(vanilla_jar(mc)), "nogui"])


def fabric(mc: str, loader_version: str) -> Server:
    installers = cached_json(f"{FABRIC_META}/versions/installer")
    installer = next(i["version"] for i in installers if i["stable"])
    url = f"{FABRIC_META}/versions/loader/{mc}/{loader_version}/{installer}/server/jar"
    launcher = download(url, CACHE / "fabric" / f"fabric-server-{mc}-{loader_version}-{installer}.jar")
    # The launcher reuses server.jar when present instead of downloading it again.
    return Server(java_major(mc), ["-jar", str(launcher), "nogui"], {"server.jar": vanilla_jar(mc)})


def forge_version(mc: str) -> str | None:
    promos = cached_json(FORGE_PROMOTIONS)["promos"]
    return promos.get(f"{mc}-latest") or promos.get(f"{mc}-recommended")


def neoforge_version(mc: str) -> str | None:
    parts = mc.split(".")
    if parts[0] == "1":
        prefix = f"{parts[1]}.{parts[2] if len(parts) > 2 else '0'}."
    else:
        prefix = f"{parts[0]}.{parts[1]}.{parts[2] if len(parts) > 2 else '0'}."
    versions = [v for v in cached_json(NEOFORGE_VERSIONS)["versions"] if v.startswith(prefix)]
    stable = [v for v in versions if "beta" not in v and "alpha" not in v]
    return (stable or versions or [None])[-1]


def _installed(kind: str, mc: str, version: str, url: str, seed: dict[str, pathlib.Path] | None = None) -> pathlib.Path:
    root = CACHE / "installs" / f"{kind}-{mc}-{version}"
    with lock_for(str(root)):
        if (root / ".installed").exists():
            return root
        installer = download(url, CACHE / "installers" / url.rsplit("/", 1)[1])
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        for name, source in (seed or {}).items():
            shutil.copy2(source, root / name)
        log(f"installing {kind} {version} for {mc}")
        result = subprocess.run(
            [str(java_executable(java_major(mc))), "-jar", str(installer), "--installServer"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{kind} installer failed:\n{result.stdout[-3000:]}\n{result.stderr[-2000:]}")
        (root / ".installed").touch()
        return root


def _from_install(root: pathlib.Path, mc: str) -> Server:
    """Turn an installer-made server folder into launch args plus files to share."""
    files = {p.name: p for p in root.iterdir() if p.name == "libraries" or p.suffix == ".jar" and "installer" not in p.name}
    script = root / ("run.bat" if os.name == "nt" else "run.sh")
    if script.exists():
        # Newer scripts run a `--onlyCheckJava` pre-check first; the launch is the last java line.
        lines = script.read_text(encoding="utf-8", errors="replace").splitlines()
        line = [l for l in lines if l.strip().startswith("java ")][-1]
        args = [a for a in line.split()[1:] if a not in ("%*", '"$@"', "$@")]
        for arg in args:
            if arg.startswith("@") and not arg.startswith("@libraries"):
                files[arg[1:]] = root / arg[1:]
        return Server(java_major(mc), args + ["nogui"], files)
    jar = next(p for p in root.glob("*forge-*.jar") if "installer" not in p.name)
    return Server(java_major(mc), ["-jar", jar.name, "nogui"], files)


# These Forge builds crash on JDK updates after 8u312 (NoSuchMethodError in
# ManifestEntryVerifier), a known ModLauncher bug, so pin the last JDK they run on.
FORGE_JDK = {"1.16.3": "jdk8u312-b07", "1.16.4": "jdk8u312-b07"}


def forge_maven_version(mc: str, version: str) -> str:
    """Old builds carry a branch suffix in Maven, such as 1.7.10-10.13.4.1614-1.7.10."""
    metadata = cached_text(f"{FORGE_MAVEN}/maven-metadata.xml")
    for full in re.findall(r"<version>([^<]+)</version>", metadata):
        if full == f"{mc}-{version}" or full.startswith(f"{mc}-{version}-"):
            return full
    raise RuntimeError(f"no Forge {version} for {mc} in Maven")


def forge(mc: str, version: str) -> Server:
    full = forge_maven_version(mc, version)
    url = f"{FORGE_MAVEN}/{full}/forge-{full}-installer.jar"
    seed = None
    if tuple(int(p) for p in mc.split(".")) < (1, 13):
        # These installers fetch the vanilla jar from a retired Amazon S3 bucket unless it is already there.
        seed = {f"minecraft_server.{mc}.jar": vanilla_jar(mc)}
    server = _from_install(_installed("forge", mc, version, url, seed), mc)
    server.java_release = FORGE_JDK.get(mc)
    return server


def fml_libraries(mc: str) -> list[str]:
    parts = tuple(int(p) for p in mc.split("."))
    if parts >= (1, 5):
        return ["argo-small-3.2.jar", "guava-14.0-rc3.jar", "asm-all-4.1.jar", "bcprov-jdk15on-148.jar", "scala-library.jar",
                f"deobfuscation_data_{mc}.zip"]
    return ["argo-2.25.jar", "guava-12.0.1.jar", "asm-all-4.0.jar"] + (["bcprov-jdk15on-147.jar"] if parts >= (1, 4, 5) else [])


def forge_jarmod(mc: str, version: str) -> Server:
    """Forge before 1.6: its universal zip goes into the vanilla server jar, and FML
    wants its libraries in lib/ before it starts."""
    full = forge_maven_version(mc, version)
    jar = CACHE / "installs" / f"forge-{mc}-{version}" / "server.jar"
    with lock_for(str(jar)):
        if not jar.exists():
            url = f"{FORGE_MAVEN}/{full}/forge-{full}-universal.zip"
            universal = download(url, CACHE / "installers" / url.rsplit("/", 1)[1])
            jar.parent.mkdir(parents=True, exist_ok=True)
            tmp = jar.with_suffix(".part")
            with zipfile.ZipFile(universal) as forge_zip, zipfile.ZipFile(vanilla_jar(mc)) as vanilla,                     zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
                patched = set(forge_zip.namelist())
                # No META-INF from either: signed Forge classes beside unsigned vanilla ones in
                # one package fail the JVM's signer check.
                for zf, keep in ((vanilla, lambda n: n not in patched), (forge_zip, lambda n: True)):
                    for info in zf.infolist():
                        if keep(info.filename) and not info.filename.startswith("META-INF/"):
                            out.writestr(info, zf.read(info.filename))
            tmp.replace(jar)
    files = {"server.jar": jar}
    for name in fml_libraries(mc):
        url, sha1 = FML_LIBRARIES[name]
        files[f"lib/{name}"] = download(url, CACHE / "fmllibs" / name, sha1=sha1)
    return Server(java_major(mc), ["-cp", "server.jar", "net.minecraft.server.MinecraftServer", "nogui"], files)


def neoforge(mc: str, version: str) -> Server:
    url = f"{NEOFORGE_MAVEN}/{version}/neoforge-{version}-installer.jar"
    return _from_install(_installed("neoforge", mc, version, url), mc)


def ornithe(mc: str, loader_version: str) -> Server:
    """Fabric Loader on 1.3.1-1.13.2, installed by Ornithe's installer next to the vanilla jar."""
    root = CACHE / "installs" / f"ornithe-{mc}-{loader_version}"
    with lock_for(str(root)):
        if not (root / "fabric-server-launch.jar").exists():
            url, sha256 = ORNITHE_INSTALLER
            installer = download(url, CACHE / "installers" / url.rsplit("/", 1)[1], sha256=sha256)
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            log(f"installing ornithe fabric {loader_version} for {mc}")
            result = subprocess.run(
                [str(java_executable(21)), "-jar", str(installer), "install", "server", mc, "fabric", loader_version,
                 f"--install-dir={root}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            if not (root / "fabric-server-launch.jar").exists():
                raise RuntimeError(f"ornithe installer failed: {result.stdout[-2000:]} {result.stderr[-2000:]}")
    files = {
        "fabric-server-launch.jar": root / "fabric-server-launch.jar",
        "libraries": root / "libraries",
        "server.jar": _without_log4j(mc),
    }
    # Fabric Loader on these old versions breaks when libraries/ is a junction, so copy it.
    return Server(java_major(mc), ["-jar", "fabric-server-launch.jar", "nogui"], files, copies=("libraries",))


def quilt_versions() -> set[str]:
    return {v["version"] for v in cached_json(f"{QUILT_META}/versions/game") if v["stable"]}


def quilt_loader_version() -> str:
    return next(v["version"] for v in cached_json(f"{QUILT_META}/versions/loader") if "-" not in v["version"])


def quilt(mc: str, loader_version: str) -> Server:
    """Quilt Loader, which also runs Fabric mods, installed by Quilt's installer next to the vanilla jar."""
    root = CACHE / "installs" / f"quilt-{mc}-{loader_version}"
    with lock_for(str(root)):
        if not (root / "quilt-server-launch.jar").exists():
            url, sha256 = QUILT_INSTALLER
            installer = download(url, CACHE / "installers" / url.rsplit("/", 1)[1], sha256=sha256)
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            log(f"installing quilt {loader_version} for {mc}")
            result = subprocess.run(
                [str(java_executable(21)), "-jar", str(installer), "install", "server", mc, loader_version,
                 f"--install-dir={root}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            if not (root / "quilt-server-launch.jar").exists():
                raise RuntimeError(f"quilt installer failed: {result.stdout[-2000:]} {result.stderr[-2000:]}")
    files = {p.name: p for p in root.iterdir() if p.name != "server.jar"}
    files["server.jar"] = vanilla_jar(mc)
    return Server(java_major(mc), ["-jar", "quilt-server-launch.jar", "nogui"], files)


def _without_log4j(mc: str) -> pathlib.Path:
    """The old server jars bundle their own log4j. Depending on the instance path, Fabric
    Loader may load it ahead of the newer log4j it ships and fail at boot, so drop it."""
    target = CACHE / "vanilla-nolog4j" / mc / "server.jar"
    with lock_for(str(target)):
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".part")
            with zipfile.ZipFile(vanilla_jar(mc)) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    if not info.filename.startswith("org/apache/logging/log4j/"):
                        dst.writestr(info, src.read(info.filename))
            tmp.replace(target)
    return target


def fill_versions(project: str) -> list[str]:
    groups = cached_json(f"{FILL}/{project}")["versions"]
    return [v for versions in groups.values() for v in versions if re.fullmatch(r"[\d.]+", v)]


def paper(mc: str, project: str = "paper") -> Server:
    builds = cached_json(f"{FILL}/{project}/versions/{mc}/builds")
    build = next((b for b in builds if b["channel"] == "STABLE"), builds[0])
    jar_info = build["downloads"]["server:default"]
    jar = download(jar_info["url"], CACHE / project / jar_info["name"], sha256=jar_info["checksums"]["sha256"])
    # Paperclip reuses a Mojang jar already in its cache folder instead of downloading it.
    files = {f"cache/mojang_{mc}.jar": vanilla_jar(mc)}
    return Server(java_major(mc), [SKIP_OUTDATED_WAIT, "-jar", str(jar), "nogui"], files, "plugins")


def purpur(mc: str) -> Server:
    info = cached_json(f"{PURPUR_API}/{mc}/latest")
    jar = download(f"{PURPUR_API}/{mc}/{info['build']}/download", CACHE / "purpur" / f"purpur-{mc}-{info['build']}.jar", md5=info["md5"])
    files = {f"cache/mojang_{mc}.jar": vanilla_jar(mc)}
    return Server(java_major(mc), [SKIP_OUTDATED_WAIT, "-jar", str(jar), "nogui"], files, "plugins")


def spigot(mc: str) -> Server:
    """Spigot has no binary downloads; BuildTools compiles it from source (slow, cached)."""
    out = CACHE / "spigot" / mc
    jar = out / f"spigot-{mc}.jar"
    with lock_for(str(out)):
        if not jar.exists():
            tool = download(BUILDTOOLS, CACHE / "buildtools" / "BuildTools.jar")
            work = CACHE / "buildtools" / f"work-{mc}"
            work.mkdir(parents=True, exist_ok=True)
            log(f"building spigot {mc} with BuildTools")
            result = subprocess.run(
                [str(java_executable(java_major(mc))), "-jar", str(tool), "--rev", mc, "--output-dir", str(out)],
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
            )
            if result.returncode != 0 or not jar.exists():
                raise RuntimeError(f"BuildTools failed for {mc}: {result.stdout[-3000:]}")
    return Server(java_major(mc), [SKIP_OUTDATED_WAIT, "-jar", str(jar), "nogui"], {}, "plugins")


class Process:
    def __init__(self, args: list[str], workdir: pathlib.Path):
        self.lines: list[str] = []
        self._cond = threading.Condition()
        self.process = subprocess.Popen(
            args,
            cwd=workdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        for line in self.process.stdout:
            with self._cond:
                self.lines.append(line.rstrip("\n"))
                self._cond.notify_all()
        with self._cond:
            self._cond.notify_all()

    def wait_for(self, pattern: str, timeout: float, start: int = 0) -> re.Match | None:
        regex = re.compile(pattern)
        deadline = time.monotonic() + timeout
        index = start
        with self._cond:
            while True:
                while index < len(self.lines):
                    match = regex.search(self.lines[index])
                    if match:
                        return match
                    index += 1
                remaining = deadline - time.monotonic()
                if remaining <= 0 or self.process.poll() is not None:
                    return None
                self._cond.wait(min(remaining, 1.0))

    def command(self, text: str) -> int:
        with self._cond:
            mark = len(self.lines)
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()
        return mark

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                self.command("stop")
                self.process.wait(timeout=90)
            except (OSError, subprocess.TimeoutExpired):
                self.kill()
        self._reader.join(timeout=10)

    def kill(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()


def remove_instance(workdir: pathlib.Path) -> None:
    if not workdir.exists():
        return
    # Drop links into the shared cache first so nothing can delete through them.
    for child in workdir.iterdir():
        if child.is_junction():
            os.rmdir(child)
        elif child.is_symlink():
            child.unlink()
    shutil.rmtree(workdir)


def prepare_instance(name: str, server: Server, port: int, content: list[pathlib.Path] = ()) -> pathlib.Path:
    workdir = RUN / name
    remove_instance(workdir)
    (workdir / "world").mkdir(parents=True)
    for target, source in server.files.items():
        (workdir / target).parent.mkdir(parents=True, exist_ok=True)
        if target in server.copies:
            (shutil.copytree if source.is_dir() else shutil.copy2)(source, workdir / target)
        else:
            link(source, workdir / target)
    folder = workdir / server.content_folder
    folder.mkdir(parents=True, exist_ok=True)
    for item in content:
        shutil.copy2(item, folder / item.name)
    (workdir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    properties = {
        "online-mode": "false",
        "server-port": str(port),
        "server-ip": "127.0.0.1",
        "level-type": "flat",
        "generate-structures": "false",
        "spawn-protection": "0",
        "spawn-monsters": "false",
        # spawn-monsters alone still let a slime kill the bot on 26.1.2.
        "difficulty": "0",
        "view-distance": "4",
        "simulation-distance": "4",
        "max-tick-time": "-1",
        "allow-flight": "true",
        "enforce-secure-profile": "false",
        "motd": "mctest",
    }
    (workdir / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in properties.items()), encoding="utf-8")
    ops = [{"uuid": offline_uuid(n), "name": n, "level": 4, "bypassesPlayerLimit": False} for n in BOT_NAMES]
    (workdir / "ops.json").write_text(json.dumps(ops), encoding="utf-8")
    # Servers before 1.7.6 read operators by name from ops.txt.
    (workdir / "ops.txt").write_text("".join(f"{n}\n" for n in BOT_NAMES), encoding="utf-8")
    return workdir


def start(server: Server, workdir: pathlib.Path) -> Process:
    # Headless: without a console, some servers (CraftBukkit 1.14-1.17) pop a desktop
    # "don't double-click the jar" dialog and hang.
    jvm = ["-Xms512M", "-Xmx2G", "-Djava.awt.headless=true", "-Dlog4j2.formatMsgNoLookups=true"]
    return Process([str(java_executable(server.java_major, server.java_release)), *jvm, *server.args], workdir)


def start_viaproxy(workdir: pathlib.Path, server_port: int, target: str) -> tuple[Process, int]:
    url, sha256 = VIAPROXY
    jar = download(url, CACHE / "viaproxy" / url.rsplit("/", 1)[1], sha256=sha256)
    proxy_dir = workdir / "viaproxy"
    proxy_dir.mkdir(exist_ok=True)
    port = free_port()
    args = [
        str(java_executable(21)),
        "-jar",
        str(jar),
        "cli",
        "--bind-address",
        f"127.0.0.1:{port}",
        "--target-address",
        f"127.0.0.1:{server_port}",
        "--target-version",
        target,
    ]
    proxy = Process(args, proxy_dir)
    proxy.wait_for(r"Binding proxy server to", timeout=90)
    proxy.wait_for(r"Finished mapping loading", timeout=60)
    return proxy, port


def run_bot(
    scenarios: list[str], port: int, version: str, workdir: pathlib.Path, timeout: float = 150, warmup: bool = False
) -> dict:
    """Run each scenario in a fresh session: before 1.17 the bot's inventory view
    goes stale after a container closes, so scenarios can't share one."""
    node = shutil.which("node")
    if node is None:
        return {"ok": False, "error": "node not found"}
    proxy = None
    client_version = BOT_ALIASES.get(version, version)
    results: dict = {}
    try:
        if version in VIA_ROUTES:
            client_version, target = VIA_ROUTES[version]
            proxy, port = start_viaproxy(workdir, port, target)
        env = dict(os.environ, MCTEST_NO_MOVEMENT="1" if version in NO_MOVEMENT else "0", MCTEST_SERVER_VERSION=version)
        if warmup:
            _bot_session(node, "warmup", port, client_version, env, timeout, "warmup")
        for scenario, name in zip(scenarios, BOT_NAMES):
            results[scenario] = _bot_session(node, scenario, port, client_version, env, timeout, name)
    finally:
        if proxy is not None:
            proxy.kill()
    return {"ok": all(r.get("ok", False) for r in results.values()), "scenarios": results}


def _bot_session(node: str, scenario: str, port: int, client_version: str, env: dict, timeout: float, name: str) -> dict:
    try:
        result = subprocess.run(
            [node, str(BOT / "craft.js"), "127.0.0.1", str(port), client_version, scenario, name],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "bot timed out"}
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    tail = (result.stdout + result.stderr).strip().splitlines()[-15:]
    return {"ok": False, "error": "bot gave no result", "output": tail}


def server_log(workdir: pathlib.Path, process: Process) -> list[str]:
    """Console output plus the logs where Forge lists its mods: debug.log before 1.17,
    and FML's own log before 1.7."""
    extra = []
    for log_file in (workdir / "logs" / "debug.log", workdir / "ForgeModLoader-server-0.log"):
        if log_file.exists():
            extra += log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return process.lines + extra


def scan_errors(lines: list[str], needles: tuple[str, ...]) -> list[str]:
    bad = re.compile(r"ERROR|WARN|Couldn't|Parsing error|Failed|Exception", re.IGNORECASE)
    return [line for line in lines if any(n in line for n in needles) and bad.search(line)]
