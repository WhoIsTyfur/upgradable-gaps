/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps;

import net.minecraft.inventory.RecipeInputInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;

public final class NotchAppleRecipes {

	public static final int CENTRE_SLOT = 4;
	public static final int INGOTS_PER_SLOT_WITH_GOLDEN_APPLE = 8;
	public static final int NO_MATCH = 0;

	private NotchAppleRecipes() {
	}

	public static int ingotsPerSlot(RecipeInputInventory grid) {
		if (grid.getWidth() != 3 || grid.getHeight() != 3 || grid.size() < 9) {
			return NO_MATCH;
		}

		if (!grid.getStack(CENTRE_SLOT).isOf(Items.GOLDEN_APPLE)) {
			return NO_MATCH;
		}

		for (int slot = 0; slot < 9; slot++) {
			if (slot == CENTRE_SLOT) {
				continue;
			}
			ItemStack stack = grid.getStack(slot);
			if (stack.isEmpty() || !stack.isOf(Items.GOLD_INGOT) || stack.getCount() < INGOTS_PER_SLOT_WITH_GOLDEN_APPLE) {
				return NO_MATCH;
			}
		}

		return INGOTS_PER_SLOT_WITH_GOLDEN_APPLE;
	}

	public static ItemStack createResult() {
		return new ItemStack(Items.ENCHANTED_GOLDEN_APPLE);
	}
}
