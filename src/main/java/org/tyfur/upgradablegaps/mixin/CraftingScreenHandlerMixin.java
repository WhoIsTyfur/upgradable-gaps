/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.mixin;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.inventory.CraftingResultInventory;
import net.minecraft.inventory.RecipeInputInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.network.packet.s2c.play.ScreenHandlerSlotUpdateS2CPacket;
import net.minecraft.recipe.CraftingRecipe;
import net.minecraft.recipe.RecipeEntry;
import net.minecraft.screen.CraftingScreenHandler;
import net.minecraft.screen.ScreenHandler;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.world.World;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.tyfur.upgradablegaps.NotchAppleRecipes;

@Mixin(CraftingScreenHandler.class)
public class CraftingScreenHandlerMixin {

	// RETURN, not HEAD: vanilla always rewrites the result slot (EMPTY when no
	// recipe matches), so ours has to go in after it.
	@Inject(
		method = "updateResult(Lnet/minecraft/screen/ScreenHandler;Lnet/minecraft/world/World;Lnet/minecraft/entity/player/PlayerEntity;Lnet/minecraft/inventory/RecipeInputInventory;Lnet/minecraft/inventory/CraftingResultInventory;Lnet/minecraft/recipe/RecipeEntry;)V",
		at = @At("RETURN")
	)
	private static void upgradablegaps$overrideResult(
			ScreenHandler handler,
			World world,
			PlayerEntity player,
			RecipeInputInventory craftingInventory,
			CraftingResultInventory resultInventory,
			RecipeEntry<CraftingRecipe> recipe,
			CallbackInfo ci) {
		if (world.isClient || !(player instanceof ServerPlayerEntity serverPlayer)) {
			return;
		}

		if (NotchAppleRecipes.ingotsPerSlot(craftingInventory) == NotchAppleRecipes.NO_MATCH) {
			return;
		}

		ItemStack result = NotchAppleRecipes.createResult();
		resultInventory.setStack(0, result);

		// This pattern has no RecipeEntry. Clear vanilla's stale one so
		// onCrafted doesn't credit or unlock the wrong recipe.
		resultInventory.setLastRecipe(null);

		handler.setPreviousTrackedSlot(0, result);
		serverPlayer.networkHandler.sendPacket(
			new ScreenHandlerSlotUpdateS2CPacket(handler.syncId, handler.nextRevision(), 0, result)
		);
	}
}
