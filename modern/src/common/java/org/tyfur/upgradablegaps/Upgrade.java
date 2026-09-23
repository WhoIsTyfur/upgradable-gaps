/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps;

import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

public final class Upgrade {
    public static final int CENTER = 4;
    public static final int INGOTS_PER_SLOT = 8;

    private Upgrade() {
    }

    public static boolean matches(CraftingContainer grid) {
        if (grid.getWidth() != 3 || grid.getHeight() != 3) {
            return false;
        }
        for (int slot = 0; slot < 9; slot++) {
            ItemStack stack = grid.getItem(slot);
            boolean ok = slot == CENTER
                    ? stack.getItem() == Items.GOLDEN_APPLE
                    : stack.getItem() == Items.GOLD_INGOT && stack.getCount() >= INGOTS_PER_SLOT;
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    public static ItemStack result() {
        return new ItemStack(Items.ENCHANTED_GOLDEN_APPLE);
    }

    public static void consume(CraftingContainer grid) {
        for (int slot = 0; slot < 9; slot++) {
            grid.removeItem(slot, slot == CENTER ? 1 : INGOTS_PER_SLOT);
        }
    }
}
