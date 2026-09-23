<!--
Copyright (c) 2026 Tyler Fursman

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
-->

# Upgradable Gaps

Upgrade a golden apple into an enchanted golden apple. Everything is
server-side: vanilla clients can connect without installing anything, and it
works in singleplayer too.

Built for **Fabric (and Quilt) 1.14 - 26.3**, **NeoForge 1.20.2 - 26.3** and
**Forge 1.15.2 - 26.3**.

## The recipe

Put **8 gold ingots in each** of the 8 outer slots of a crafting table, with a
golden apple in the centre. That is 64 ingots plus the golden apple's 8: the
same 72 ingots' worth of gold as the old notch apple recipe.

## Why this needs a mod

Vanilla crafting cannot express "a stack of items in one slot". An
`Ingredient` in recipe JSON has no count field, and `ResultSlot#onTake`
removes exactly one item from every filled slot. A data pack recipe asking for gold ingots around a golden apple
would cost 8 ingots, not 64, and there is no JSON knob that changes it.

So the mod does two things with Mixin:

- **`CraftingMenuMixin`** puts the enchanted apple in the result slot when the
  grid matches.
- **`ResultSlotMixin`** takes 8 ingots from each outer slot, instead of one,
  when it is crafted.

It registers **nothing** into any registry and adds no recipe serializer. That
is what keeps vanilla clients able to join: since 1.13 the server sends every
recipe to every client on login, and a vanilla client cannot decode a recipe
type it doesn't have.

## Installing

Drop the jar for your loader and Minecraft version into `<server>/mods/` and
restart. Jars are named `upgradable-gaps-<version>+<loader>-mc<versions>.jar`.

- **Fabric / Quilt:** any Fabric Loader 0.14+. No Fabric API needed.
- **NeoForge:** any build for your Minecraft version.
- **Forge:** 1.15.2 needs Forge 31.2.44 or newer (the first with Mixin).

## Building

The mod lives in `modern/`, one Gradle build with a subproject per loader and
Minecraft range (`modern/targets/<loader>-<versions>/gradle.properties`).
Gradle must run on **JDK 25**; older targets are compiled with `--release`.

```
cd modern
./gradlew build                                  # every target
./gradlew :fabric-1.21-1.21.1:build              # one target
```

Jars land in `modern/targets/<target>/build/libs/`.

Mixin target signatures changed several times, so the source is split by what
actually changed rather than by version:

- `src/common` -- the recipe itself (`Upgrade`), the same for every version.
- `src/menu/<first version>` -- `CraftingMenuMixin`, one variant per signature
  of `slotChangedCraftingGrid` (1.14.4, 1.17, 1.17.1, 1.21, 1.21.2).
- `src/slot/<first version>` -- `ResultSlotMixin` (1.14.4, 1.17).
- `src/fabric`, `src/neoforge`, `src/neoforge-1.20.2`, `src/forge` -- loader
  metadata and entry points.

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

## Tuning the amount

`Upgrade` holds the constant:

```java
public static final int INGOTS_PER_SLOT = 8;
```

Both the match and the consumption read from it, so they stay in step. Change
it and rebuild.
