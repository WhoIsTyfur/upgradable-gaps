/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.mixin;

import net.minecraft.network.protocol.game.ClientboundContainerSetSlotPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.CraftingMenu;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.tyfur.upgradablegaps.Upgrade;

@Mixin(CraftingMenu.class)
public class CraftingMenuMixin {

    // RETURN: vanilla always rewrites the result slot, so the upgrade goes in after it.
    @Inject(method = "slotChangedCraftingGrid", at = @At("RETURN"))
    private static void upgradablegaps$showResult(AbstractContainerMenu menu, Level level, Player player, CraftingContainer craftSlots,
            ResultContainer resultSlots, CallbackInfo ci) {
        if (level.isClientSide || !(player instanceof ServerPlayer) || !Upgrade.matches(craftSlots)) {
            return;
        }
        ItemStack result = Upgrade.result();
        resultSlots.setItem(0, result);
        // No recipe backs this result; clear vanilla's so it is not credited or unlocked.
        resultSlots.setRecipeUsed(null);
        menu.setRemoteSlot(0, result);
        ((ServerPlayer) player).connection.send(
                new ClientboundContainerSetSlotPacket(menu.containerId, menu.incrementStateId(), 0, result));
    }
}
