#!/usr/bin/env python3
# Copyright (c) 2026 Tyler Fursman
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Run the Bukkit plugin on Paper, Folia, Purpur and Spigot servers and craft with a bot."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys

import mctest

JAR_GLOB = "upgradable-gaps-*+bukkit.jar"
SCENARIOS = ["upgrade", "upgradeBatch", "upgradeShort", "vanillaGoldenApple"]

# Purpur and Spigot are Paper's parent and fork; a spread of versions is enough.
PURPUR_SAMPLE = ["1.14.4", "1.16.5", "1.18.2", "1.20.1", "1.21.1", "1.21.11", "26.3"]
SPIGOT_SAMPLE = ["1.8.8", "1.12.2", "1.16.5", "1.20.4", "1.21.1", "26.3"]


def versions_for(platform: str) -> list[str]:
    if platform in ("paper", "folia"):
        return sorted(mctest.fill_versions(platform), key=lambda v: tuple(int(x) for x in v.split(".")))
    return {"purpur": PURPUR_SAMPLE, "spigot": SPIGOT_SAMPLE}[platform]


def server_for(platform: str, mc: str) -> mctest.Server:
    if platform in ("paper", "folia"):
        return mctest.paper(mc, platform)
    return {"purpur": mctest.purpur, "spigot": mctest.spigot}[platform](mc)


def test_one(jar, platform: str, mc: str) -> dict:
    report: dict = {"platform": platform, "version": mc}
    server = server_for(platform, mc)
    port = mctest.free_port()
    workdir = mctest.prepare_instance(f"{platform}@{mc}", server, port, [jar])
    process = mctest.start(server, workdir)
    try:
        if not process.wait_for(r"Done \(", timeout=900):
            report.update(ok=False, error="server did not finish starting", tail=process.lines[-40:])
            return report
        report["loaded"] = any("Enabling UpgradableGaps" in line for line in process.lines)
        report["bot"] = mctest.run_bot(SCENARIOS, port, mc, workdir)
        report["errors"] = mctest.scan_errors(process.lines, ("UpgradableGaps", "upgradablegaps"))
        report["ok"] = report["loaded"] and not report["errors"] and report["bot"].get("ok", False)
        if not report["ok"]:
            report["tail"] = process.lines[-40:]
        return report
    finally:
        process.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platforms", default="paper,folia,purpur,spigot")
    parser.add_argument("--versions", default="", help="only these Minecraft versions")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    jars = sorted((mctest.ROOT / "bukkit" / "build" / "libs").glob(JAR_GLOB))
    jars = [j for j in jars if not j.name.endswith("-sources.jar")]
    if not jars:
        parser.error("build the plugin first (cd bukkit && ./gradlew build)")
    if not (mctest.BOT / "node_modules").exists():
        parser.error("run `npm ci` in test/bot first")
    only = {v for v in args.versions.split(",") if v}

    jobs = [(p, v) for p in args.platforms.split(",") for v in versions_for(p) if not only or v in only]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(test_one, jars[-1], p, v): (p, v) for p, v in jobs}
        for future in concurrent.futures.as_completed(futures):
            platform, version = futures[future]
            try:
                report = future.result()
            except Exception as exc:  # noqa: BLE001 - one broken server must not stop the rest
                report = {"platform": platform, "version": version, "ok": False, "error": repr(exc)}
            results.append(report)
            mctest.log(f"{'PASS' if report['ok'] else 'FAIL'}  {platform} @ {version}")

    order = {job: i for i, job in enumerate(jobs)}
    results.sort(key=lambda r: order[(r["platform"], r["version"])])
    mctest.RUN.mkdir(exist_ok=True)
    (mctest.RUN / "plugin-results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    failed = [f"{r['platform']}@{r['version']}" for r in results if not r["ok"]]
    mctest.log(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
