# Upgradable Gaps

Upgrade a golden apple into an enchanted golden apple. Everything is
server-side: players need nothing extra (except on very old Forge, see
*Installing*), and it works in singleplayer too.

| Server | Minecraft | Jar |
| --- | --- | --- |
| Fabric, Quilt | 1.14 - 26.3 | `+fabric-mc<versions>` |
| Ornithe (Fabric Loader on old versions) | 1.3.1 - 1.13.2 | `+ornithe-mc<versions>` |
| Forge | 1.3.2 - 26.3 | `+forge-mc<versions>` |
| NeoForge | 1.20.2 - 26.3 | `+neoforge-mc<versions>` |
| Bukkit, Spigot, Paper, Purpur, Folia | 1.7.10 - 26.3 | `+bukkit` (one jar for all) |

The Forge range skips the Minecraft versions Forge itself never shipped (1.16,
1.17, 1.20.5, 1.21.2 and so on).

## The recipe

Put **8 gold ingots in each** of the 8 outer slots of a crafting table, with a
golden apple in the centre. That is 64 ingots plus the golden apple's 8: the
same 72 ingots' worth of gold as the old notch apple recipe.

## Why this needs a mod

Vanilla crafting cannot express "a stack of items in one slot". An
`Ingredient` in recipe JSON has no count field, and the result slot removes
exactly one item from every filled slot. A data pack recipe asking for gold
ingots around a golden apple would cost 8 ingots, not 64, and there is no JSON
knob that changes it.

So every build does the same two things: when the grid matches, it puts the
enchanted apple in the result slot and sends it to the player; when the player
takes it, it removes 8 ingots from each outer slot instead of one. How it
hooks in depends on the platform:

- **Mixin** (Fabric, Quilt, NeoForge, Forge 1.15.2+, Ornithe): one mixin on
  the crafting menu's grid update and one on the result slot.
- **JS coremods** (Forge 1.13.2 - 1.15.1, which has no Mixin): the same two
  hooks, injected through Forge's own coremod system.
- **A registered recipe plus crafting events** (Forge 1.3.2 - 1.12.2): before
  1.13 the server never sends its recipes to clients, so a real recipe is safe
  there.
- **Inventory events** (the plugin): it cancels the click on the result slot
  and does the craft itself.

On 1.13 and newer it registers **nothing** into any registry and adds no
recipe serializer. That is what keeps vanilla clients able to join: since 1.13
the server sends every recipe to every client on login, and a vanilla client
cannot decode a recipe type it doesn't have.

## Installing

Drop the jar for your server and Minecraft version into `mods/` (or
`plugins/` for the plugin) and restart. Jars are named
`upgradable-gaps-<version>+<platform>-mc<versions>.jar`.

- **Fabric / Quilt:** any Fabric Loader 0.14+, or Quilt Loader. No Fabric API
  needed.
- **Ornithe:** install Fabric Loader with the Ornithe installer first; these
  jars do not run on Legacy Fabric.
- **Forge 1.15.2** needs Forge 31.2.44 or newer (the first with Mixin).
- **Forge 1.3.2 - 1.7.10:** Forge servers this old turn vanilla clients away,
  so players need Forge installed. They do not need this mod.
- **Forge 1.3.2 - 1.5.2** has one jar per Minecraft version: Forge that old
  loads mods by obfuscated names, which change with every release.
- **Forge 1.7.2** only starts on Java 7; the one jar covers 1.7.2 and 1.7.10.
- **NeoForge:** any build for your Minecraft version.
- **Plugin:** one jar for every Bukkit-based server from 1.7.10 on, Folia
  included.

## Things worth knowing

- **Recipe book.** The recipe doesn't appear in it, and that is a hard vanilla
  limit: the recipe book renders one item per slot with no count, and its
  click-to-fill places one item per slot. An entry would fill the grid with
  8 ingots and then not craft, which is worse than no entry. It works fine
  arranged by hand -- you'll want to tell players about it.
- **The vanilla golden apple recipe is untouched.** Nothing overrides, removes
  or edits it, and this recipe cannot collide with it: its centre is a golden
  apple, not an apple.
- **Batch crafting works.** Stack golden apples in the centre and 8 ingots per
  apple in each outer slot, then shift-click the result to craft several at
  once.
- **Crafters.** The recipe does not work in a Crafter block. A Crafter
  consumes exactly one item per slot and resolves recipes through the recipe
  manager, which knows nothing about this pattern. That is deliberate --
  letting it through would let a Crafter make notch apples for 8 ingots and a
  golden apple. Other auto-crafting mods will behave the same way, for the same
  reason.
- **`doLimitedCrafting`.** The recipe ignores that game rule and stays
  craftable, because there is no recipe entry for a player to unlock.
- **Vanilla clients see a one-frame flicker** of the input slots when crafting:
  their local prediction assumes one ingot per slot, and the server's
  correction arrives a tick later. Cosmetic only -- the server is
  authoritative.

## Building

`python build.py` builds everything, copies the release jars to `dist/` and
writes `dist/manifest.json` for `publish.py`. It fetches the JDKs it needs
from Adoptium, so nothing needs installing first. To build one part by hand:

| Folder | What | Gradle runs on | Tool |
| --- | --- | --- | --- |
| `modern/` | Fabric 1.14+, Forge 1.15.2+, NeoForge | JDK 25 | Architectury Loom |
| `ornithe/` | Ornithe 1.3.1 - 1.13.2 | JDK 25 | Fabric Loom + Ploceus |
| `forge-legacy/` | Forge 1.3.2 - 1.15.1 | JDK 21 | Unimined |
| `bukkit/` | the plugin | JDK 25 | plain Gradle |

```
cd modern
./gradlew build                                  # every target
./gradlew :fabric-1.21-1.21.1:build              # one target
```

Each build has one subproject per loader and Minecraft range, described by
`targets/<name>/gradle.properties`; jars land in
`targets/<name>/build/libs/`. Older targets compile with `--release`, so one
JDK builds them all.

Source is split by what actually changed rather than by version:

- `modern/src/common` -- the recipe (`Upgrade`); `modern/src/menu/<first
  version>` and `modern/src/slot/<first version>` -- one mixin variant per
  signature change; `modern/src/<loader>` -- metadata and entry points.
- `ornithe/src/{upgrade,menu,slot}/<first version>` -- the same split for the
  old versions, in Feather names.
- `forge-legacy/src/<era>` -- one source tree per Forge API era;
  `src/<era>-selftest` holds the test-only mod described below.

## Testing

`test/` provisions real servers (official vanilla jars and installers, cached
under `~/.cache/mctest`) and crafts on them with a
[mineflayer](https://github.com/PrismarineJS/mineflayer) bot. Minecraft
versions the bot cannot speak go through
[ViaProxy](https://github.com/ViaVersion/ViaProxy). Each scenario checks the
server's truth by logging in again: the upgrade, a shift-click batch, one
ingot short (nothing may happen), and the vanilla golden apple recipe still
working.

```
cd test/bot && npm ci && cd ../..
python test/test_mods.py --jobs 6        # every mod jar on every version it claims
python test/test_plugin.py --jobs 4      # the plugin on Paper, Folia, Purpur, Spigot
python test/test_mods.py --targets fabric-26.1-26.3 --versions 26.3   # one run
```

Forge servers up to 1.7.10 refuse vanilla clients, so for them a small
test-only mod crafts through a real workbench menu on the server instead and
logs `UPGRADABLEGAPS-SELFTEST PASS`. Forge 1.3.2 - 1.5.2 also download
libraries at start from a host that is gone; the harness takes them from
Prism Launcher's mirror and checks each against the SHA-1 FML expects. Forge
1.7.2 needs a Java 7 JDK, which Adoptium does not ship: put one (Azul Zulu 7
or Oracle 7u80) in `~/.cache/mctest/jdk/7/`. Results go to `run/results.json` and
`run/plugin-results.json`.

## Releasing

Set `mod_version` in the four `gradle.properties`, add a `CHANGELOG.md`
section, then push a `v<version>` tag. `.github/workflows/release.yml` builds,
uploads every jar and creates a GitHub release. It needs these repository
secrets and variables; a platform without them is skipped:

| Platform | Secret | Variable | Gets |
| --- | --- | --- | --- |
| Modrinth | `MODRINTH_TOKEN` | `MODRINTH_PROJECT_ID` | every jar |
| CurseForge | `CURSEFORGE_TOKEN` | `CURSEFORGE_PROJECT_ID` | mod jars except Ornithe |
| Hangar | `HANGAR_API_KEY` | `HANGAR_PROJECT` | the plugin |

Two plugin pages take the `+bukkit` jar from the GitHub release by hand:
SpigotMC, which has no upload API, and the CurseForge Bukkit Plugins project,
whose API (on dev.bukkit.org) only takes a legacy Twitch login.
`python publish.py --dry-run` prints every upload without sending anything.

If a run fails partway, fix the scripts on `main`, delete whatever the failed run
already put on Modrinth (it would upload those again), then use **Actions ->
Release -> Run workflow** with the same tag.

## Tuning the amount

`INGOTS_PER_SLOT` is the constant, in each source tree (`Upgrade` in
`modern/src/common`, and its counterparts in `ornithe/`, `forge-legacy/` and
`bukkit/`). Both the match and the consumption read from it, so they stay in
step. Change it everywhere and rebuild.

## License

Copyright (c) 2026 Tyler Fursman. Licensed under the
[Mozilla Public License 2.0](LICENSE).
