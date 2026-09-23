package org.tyfur.craftablenotchapples.mixin;

import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.inventory.RecipeInputInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.screen.slot.CraftingResultSlot;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.tyfur.craftablenotchapples.NotchAppleRecipes;

@Mixin(CraftingResultSlot.class)
public abstract class CraftingResultSlotMixin {

	@Shadow
	@Final
	private RecipeInputInventory input;

	@Shadow
	protected abstract void onCrafted(ItemStack stack);

	@Inject(
		method = "onTakeItem(Lnet/minecraft/entity/player/PlayerEntity;Lnet/minecraft/item/ItemStack;)V",
		at = @At("HEAD"),
		cancellable = true
	)
	private void craftablenotchapples$consumeWholeStacks(PlayerEntity player, ItemStack stack, CallbackInfo ci) {
		int perSlot = NotchAppleRecipes.ingotsPerSlot(this.input);
		if (perSlot == NotchAppleRecipes.NO_MATCH) {
			return;
		}

		this.onCrafted(stack);

		for (int slot = 0; slot < 9; slot++) {
			int amount = (slot == NotchAppleRecipes.CENTRE_SLOT) ? 1 : perSlot;
			this.input.removeStack(slot, amount);
		}

		// Must cancel, not trim the grid and let vanilla finish: with no recipe
		// match, vanilla's remainder pass merges live grid stacks back (item dupe).
		ci.cancel();
	}
}
