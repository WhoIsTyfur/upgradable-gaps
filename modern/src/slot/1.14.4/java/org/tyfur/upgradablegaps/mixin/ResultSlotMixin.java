/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.mixin;

import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.ResultSlot;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.tyfur.upgradablegaps.Upgrade;

@Mixin(ResultSlot.class)
public abstract class ResultSlotMixin {

    @Shadow
    @Final
    private CraftingContainer craftSlots;

    @Shadow
    protected abstract void checkTakeAchievements(ItemStack stack);

    @Inject(method = "onTake", at = @At("HEAD"), cancellable = true)
    private void upgradablegaps$takeResult(Player player, ItemStack stack, CallbackInfoReturnable<ItemStack> callback) {
        if (!Upgrade.matches(this.craftSlots)) {
            return;
        }
        this.checkTakeAchievements(stack);
        Upgrade.consume(this.craftSlots);
        // Cancel rather than trim the grid and let vanilla finish: with no recipe
        // matched, its remainder pass copies the grid back in (an item dupe).
        callback.setReturnValue(stack);
    }
}
