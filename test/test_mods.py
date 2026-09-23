#!/usr/bin/env python3
# Copyright (c) 2026 Tyler Fursman
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Run every built mod jar on every Minecraft version it claims and craft with a bot."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import sys

import mctest

BUILDS = [mctest.ROOT / "modern", mctest.ROOT / "ornithe"]
SCENARIOS = ["upgrade", "upgradeBatch", "upgradeShort", "vanillaGoldenApple"]
MOD_ID = "upgradablegaps"
MIXIN_FAILURE = re.compile(r"InvalidInjectionException|InjectionError|MixinApplyError|Mixin apply .*failed|Critical injection failure")


def read_properties(path: pathlib.Path) -> dict[str, str]:
    props = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def all_targets() -> list[dict]:
    targets = []
    for build in BUILDS:
        loader_version = read_properties(build / "gradle.properties")["fabric_loader_version"]
        for folder in sorted((build / "targets").iterdir()):
            props = read_properties(folder / "gradle.properties")
            jars = [j for j in (folder / "build" / "libs").glob("*.jar") if not j.name.endswith("-sources.jar")]
            targets.append(
                {
                    "name": folder.name,
                    "loader": props.get("loom.platform", "ornithe"),
                    "jar": jars[0] if jars else None,
                    "versions": props["game_versions"].split(","),
                    "fabric_loader": loader_version,
                }
            )
    return targets


def server_for(target: dict, mc: str) -> tuple[mctest.Server | None, str]:
    loader = target["loader"]
    if loader == "fabric":
        return mctest.fabric(mc, target["fabric_loader"]), target["fabric_loader"]
    if loader == "ornithe":
        return mctest.ornithe(mc, target["fabric_loader"]), target["fabric_loader"]
    if loader == "forge":
        version = mctest.forge_version(mc)
        return (mctest.forge(mc, version) if version else None), version
    if loader == "neoforge":
        version = mctest.neoforge_version(mc)
        return (mctest.neoforge(mc, version) if version else None), version
    raise ValueError(loader)


def test_one(target: dict, mc: str) -> dict:
    report: dict = {"target": target["name"], "version": mc}
    server, loader_version = server_for(target, mc)
    report["loader_version"] = loader_version
    if server is None:
        report.update(ok=False, error=f"no {target['loader']} build for {mc}")
        return report
    port = mctest.free_port()
    workdir = mctest.prepare_instance(f"{target['name']}@{mc}", server, port, [target["jar"]])
    process = mctest.start(server, workdir)
    try:
        if not process.wait_for(r"Done \(", timeout=900):
            report.update(ok=False, error="server did not finish starting", tail=process.lines[-40:])
            return report
        report["bot"] = mctest.run_bot(SCENARIOS, port, mc, workdir)
        lines = mctest.server_log(workdir, process)
        # Forge 1.17 only logs the jar name at INFO level.
        report["loaded"] = any(MOD_ID in line or target["jar"].name in line for line in lines)
        errors = mctest.scan_errors(lines, (MOD_ID,))
        errors += [line for line in lines if MIXIN_FAILURE.search(line)]
        report["errors"] = errors
        report["ok"] = report["loaded"] and not errors and report["bot"].get("ok", False)
        if not report["ok"]:
            report["tail"] = process.lines[-40:]
        return report
    finally:
        process.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loaders", default="fabric,forge,neoforge,ornithe")
    parser.add_argument("--targets", default="", help="comma-separated target folder names")
    parser.add_argument("--versions", default="", help="only these Minecraft versions")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    loaders = set(args.loaders.split(","))
    only_targets = {t for t in args.targets.split(",") if t}
    only_versions = {v for v in args.versions.split(",") if v}
    if not (mctest.BOT / "node_modules").exists():
        parser.error("run `npm ci` in test/bot first")

    jobs = []
    for target in all_targets():
        if target["loader"] not in loaders or (only_targets and target["name"] not in only_targets):
            continue
        if target["jar"] is None:
            parser.error(f"{target['name']} has no jar; build it first (./gradlew build in modern/ and ornithe/)")
        jobs += [(target, v) for v in target["versions"] if not only_versions or v in only_versions]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(test_one, t, v): (t["name"], v) for t, v in jobs}
        for future in concurrent.futures.as_completed(futures):
            name, version = futures[future]
            try:
                report = future.result()
            except Exception as exc:  # noqa: BLE001 - one broken server must not stop the rest
                report = {"target": name, "version": version, "ok": False, "error": repr(exc)}
            results.append(report)
            mctest.log(f"{'PASS' if report['ok'] else 'FAIL'}  {name} @ {version}")

    order = {(t["name"], v): i for i, (t, v) in enumerate(jobs)}
    results.sort(key=lambda r: order[(r["target"], r["version"])])
    mctest.RUN.mkdir(exist_ok=True)
    (mctest.RUN / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failed = [f"{r['target']}@{r['version']}" for r in results if not r["ok"]]
    mctest.log(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
