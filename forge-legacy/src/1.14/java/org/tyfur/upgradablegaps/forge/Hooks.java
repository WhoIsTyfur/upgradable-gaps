/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.entity.player.ServerPlayerEntity;
import net.minecraft.inventory.CraftResultInventory;
import net.minecraft.inventory.CraftingInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;
import net.minecraft.network.play.server.SSetSlotPacket;
import net.minecraft.world.World;

// Called from the coremods in META-INF/coremods.json; Forge before 1.15.2 has no Mixin.
public final class Hooks {
    private static final int CENTER = 4;
    private static final int INGOTS_PER_SLOT = 8;

    private Hooks() {
    }

    public static boolean arranged(CraftingInventory grid) {
        if (grid.getWidth() != 3 || grid.getHeight() != 3) {
            return false;
        }
        for (int slot = 0; slot < 9; slot++) {
            ItemStack stack = grid.getStackInSlot(slot);
            boolean ok = slot == CENTER
                    ? stack.getItem() == Items.GOLDEN_APPLE
                    : stack.getItem() == Items.GOLD_INGOT && stack.getCount() >= INGOTS_PER_SLOT;
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    // Runs at every return of the crafting table's grid update, after vanilla rewrote the result slot.
    public static void showResult(int windowId, World world, PlayerEntity player, CraftingInventory grid, CraftResultInventory result) {
        if (world.isRemote || !(player instanceof ServerPlayerEntity) || !arranged(grid)) {
            return;
        }
        ItemStack stack = new ItemStack(Items.ENCHANTED_GOLDEN_APPLE);
        result.setInventorySlotContents(0, stack);
        // No recipe backs this result; clear vanilla's so it is not credited or unlocked.
        result.setRecipeUsed(null);
        ((ServerPlayerEntity) player).connection.sendPacket(new SSetSlotPacket(windowId, 0, stack));
    }

    public static void consume(CraftingInventory grid) {
        for (int slot = 0; slot < 9; slot++) {
            grid.decrStackSize(slot, slot == CENTER ? 1 : INGOTS_PER_SLOT);
        }
    }
}
