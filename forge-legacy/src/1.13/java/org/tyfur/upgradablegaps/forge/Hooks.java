/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.init.Items;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.IInventory;
import net.minecraft.inventory.InventoryCraftResult;
import net.minecraft.inventory.InventoryCrafting;
import net.minecraft.item.ItemStack;
import net.minecraft.network.play.server.SPacketSetSlot;
import net.minecraft.world.World;

// Called from the coremods in META-INF/coremods.json; Forge before 1.15.2 has no Mixin.
public final class Hooks {
    private static final int CENTER = 4;
    private static final int INGOTS_PER_SLOT = 8;

    private Hooks() {
    }

    public static boolean arranged(InventoryCrafting grid) {
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

    // Runs at every return of the grid update, after vanilla rewrote the result slot.
    public static void showResult(Container menu, World world, EntityPlayer player, IInventory grid, InventoryCraftResult result) {
        if (world.isRemote || !(player instanceof EntityPlayerMP) || !(grid instanceof InventoryCrafting) || !arranged((InventoryCrafting) grid)) {
            return;
        }
        ItemStack stack = new ItemStack(Items.ENCHANTED_GOLDEN_APPLE);
        result.setInventorySlotContents(0, stack);
        // No recipe backs this result; clear vanilla's so it is not credited or unlocked.
        result.setRecipeUsed(null);
        ((EntityPlayerMP) player).connection.sendPacket(new SPacketSetSlot(menu.windowId, 0, stack));
    }

    public static void consume(InventoryCrafting grid) {
        for (int slot = 0; slot < 9; slot++) {
            grid.decrStackSize(slot, slot == CENTER ? 1 : INGOTS_PER_SLOT);
        }
    }
}
