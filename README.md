<!--
Copyright (c) 2026 Tyler Fursman

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
-->

# Upgradable Gaps

Upgrade a golden apple into an enchanted golden apple on **Minecraft 1.21.1
(Fabric)**. Everything is server-side: vanilla clients can connect without
installing anything.

## The recipe

Put **8 gold ingots in each** of the 8 outer slots of a crafting table, with a
golden apple in the centre. That is 64 ingots plus the golden apple's 8: the
same 72 ingots' worth of gold as the old notch apple recipe.

## Why this needs a mod

Vanilla crafting cannot express "a stack of items in one slot". An
`Ingredient` in recipe JSON has no count field, and
`CraftingResultSlot#onTakeItem` hard-codes `removeStack(slot, 1)` for every
filled slot. A data pack recipe asking for gold ingots around a golden apple
would cost 8 ingots, not 64, and there is no JSON knob that changes it.

So the mod does two things with Mixin:

- **`CraftingScreenHandlerMixin`** puts the enchanted apple in the result slot
  when the grid matches.
- **`CraftingResultSlotMixin`** takes 8 ingots from each outer slot, instead of
  one, when it is crafted.

It registers **nothing** into any registry and adds no recipe serializer. That
is what keeps vanilla clients able to join: on 1.21.1 the server sends every
recipe to every client on login, and a vanilla client cannot decode a recipe
type it doesn't have.

## Installing

Drop `upgradable-gaps-1.0.0.jar` into `<server>/mods/` and restart. Needs
Fabric Loader 0.16.0+. No Fabric API required.

## Building the jar

Needs **JDK 21**. Minecraft 1.21.1 targets Java 21, and Gradle 8.11 cannot run
on Java 24 or newer, so if your default JDK is newer than 23, uncomment
`org.gradle.java.home` in `gradle.properties` and point it at a JDK 21.

```
.\gradlew.bat build      # Windows (PowerShell or cmd)
./gradlew build          # macOS / Linux / Git Bash
```

The jar lands in `build/libs/upgradable-gaps-1.0.0.jar`. Ignore the
`-sources.jar`.

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

`NotchAppleRecipes` holds the constant:

```java
public static final int INGOTS_PER_SLOT_WITH_GOLDEN_APPLE = 8;
```

Both the match and the consumption read from it, so they stay in step. Change
it and rebuild.
