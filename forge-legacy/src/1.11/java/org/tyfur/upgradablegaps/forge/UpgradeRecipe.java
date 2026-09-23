/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import net.minecraft.init.Items;
import net.minecraft.inventory.InventoryCrafting;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.IRecipe;
import net.minecraft.util.NonNullList;
import net.minecraft.world.World;

public final class UpgradeRecipe implements IRecipe {
    private static final int CENTER = 4;
    private static final int INGOTS_PER_SLOT = 8;

    @Override
    public boolean matches(InventoryCrafting grid, World world) {
        if (grid.getSizeInventory() != 9) {
            return false;
        }
        for (int slot = 0; slot < 9; slot++) {
            ItemStack stack = grid.getStackInSlot(slot);
            boolean ok = slot == CENTER
                    ? stack.getItem() == Items.GOLDEN_APPLE && stack.getMetadata() == 0
                    : stack.getItem() == Items.GOLD_INGOT && stack.getCount() >= INGOTS_PER_SLOT;
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    @Override
    public ItemStack getCraftingResult(InventoryCrafting grid) {
        return getRecipeOutput();
    }

    @Override
    public int getRecipeSize() {
        return 9;
    }

    @Override
    public ItemStack getRecipeOutput() {
        return new ItemStack(Items.GOLDEN_APPLE, 1, 1);
    }

    // Called while the result is taken, before vanilla removes one item per slot,
    // so taking the other seven here makes eight. Doing it any later would stop
    // the grid matching, and vanilla's no-match remainder pass duplicates it.
    @Override
    public NonNullList<ItemStack> getRemainingItems(InventoryCrafting grid) {
        for (int slot = 0; slot < 9; slot++) {
            if (slot != CENTER) {
                grid.decrStackSize(slot, INGOTS_PER_SLOT - 1);
            }
        }
        return NonNullList.withSize(grid.getSizeInventory(), ItemStack.EMPTY);
    }
}
