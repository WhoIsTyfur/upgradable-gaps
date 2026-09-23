/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.mixin;

import net.minecraft.inventory.CraftingInventory;
import net.minecraft.inventory.Inventory;
import net.minecraft.network.packet.s2c.play.InventoryMenuSlotContentS2CPacket;
import net.minecraft.server.entity.living.player.ServerPlayerEntity;
import net.minecraft.inventory.menu.CraftingTableMenu;
import net.minecraft.inventory.menu.InventoryMenu;
import net.minecraft.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.tyfur.upgradablegaps.Upgrade;

// Extends the menu's superclass only to reach its protected listeners field.
@Mixin(CraftingTableMenu.class)
public abstract class CraftingTableMenuMixin extends InventoryMenu {

    @Shadow
    public CraftingInventory inventory;

    @Shadow
    public Inventory resultInventory;

    // RETURN: vanilla always rewrites the result slot, so the upgrade goes in after it.
    @Inject(method = "onContentsChanged", at = @At("RETURN"))
    private void upgradablegaps$showResult(Inventory changed, CallbackInfo ci) {
        if (!Upgrade.matches(this.inventory)) {
            return;
        }
        ItemStack result = Upgrade.result();
        this.resultInventory.setItem(0, result);
        // Servers never sync the result slot themselves; vanilla clients compute
        // it locally, which they can't do for this recipe.
        for (Object listener : this.listeners) {
            if (listener instanceof ServerPlayerEntity) {
                ((ServerPlayerEntity) listener).networkHandler.sendPacket(new InventoryMenuSlotContentS2CPacket(this.networkId, 0, result));
            }
        }
    }
}
