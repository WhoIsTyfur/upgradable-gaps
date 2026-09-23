/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import net.minecraft.init.Items;
import net.minecraft.inventory.IInventory;
import net.minecraft.inventory.InventoryCrafting;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.IRecipe;
import net.minecraft.world.World;

public final class UpgradeRecipe implements IRecipe {
    private static final int CENTER = 4;
    private static final int INGOTS_PER_SLOT = 8;

    static boolean arranged(IInventory grid) {
        if (grid.getSizeInventory() != 9) {
            return false;
        }
        for (int slot = 0; slot < 9; slot++) {
            ItemStack stack = grid.getStackInSlot(slot);
            boolean ok = slot == CENTER
                    ? stack != null && stack.getItem() == Items.golden_apple && stack.getMetadata() == 0
                    : stack != null && stack.getItem() == Items.gold_ingot && stack.stackSize >= INGOTS_PER_SLOT;
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    static void takeExtraIngots(IInventory grid) {
        for (int slot = 0; slot < 9; slot++) {
            if (slot != CENTER) {
                grid.decrStackSize(slot, INGOTS_PER_SLOT - 1);
            }
        }
    }

    @Override
    public boolean matches(InventoryCrafting grid, World world) {
        return arranged(grid);
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
        return new ItemStack(Items.golden_apple, 1, 1);
    }
}
