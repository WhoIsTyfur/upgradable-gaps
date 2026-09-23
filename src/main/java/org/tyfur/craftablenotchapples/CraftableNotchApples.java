package org.tyfur.craftablenotchapples;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Registers nothing and adds no recipe types, so vanilla clients can join. */
public class CraftableNotchApples implements ModInitializer {
	public static final String MOD_ID = "craftablenotchapples";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		LOGGER.info(
			"Enchanted golden apple recipe active: {} gold ingots per slot + golden apple.",
			NotchAppleRecipes.INGOTS_PER_SLOT_WITH_GOLDEN_APPLE
		);
	}
}
