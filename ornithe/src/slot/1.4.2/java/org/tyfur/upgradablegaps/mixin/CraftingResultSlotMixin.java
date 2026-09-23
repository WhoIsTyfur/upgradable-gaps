/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.mixin;

import net.minecraft.entity.living.player.PlayerEntity;
import net.minecraft.inventory.Inventory;
import net.minecraft.inventory.slot.CraftingResultSlot;
import net.minecraft.item.ItemStack;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.tyfur.upgradablegaps.Upgrade;

@Mixin(CraftingResultSlot.class)
public abstract class CraftingResultSlotMixin {

    @Shadow
    @Final
    private Inventory craftingInventory;

    @Shadow
    protected abstract void checkAchievements(ItemStack item);

    @Inject(method = "onItemRemoved", at = @At("HEAD"), cancellable = true)
    private void upgradablegaps$takeResult(PlayerEntity player, ItemStack item, CallbackInfo callback) {
        if (!Upgrade.matches(this.craftingInventory)) {
            return;
        }
        this.checkAchievements(item);
        Upgrade.consume(this.craftingInventory);
        // Cancel rather than trim the grid and let vanilla finish: from 1.9 on, with no
        // recipe matched, its remainder pass copies the grid back in (an item dupe).
        callback.cancel();
    }
}
