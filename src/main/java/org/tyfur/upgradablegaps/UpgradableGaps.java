/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Registers nothing and adds no recipe types, so vanilla clients can join. */
public class UpgradableGaps implements ModInitializer {
	public static final String MOD_ID = "upgradablegaps";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		LOGGER.info(
			"Enchanted golden apple recipe active: {} gold ingots per slot + golden apple.",
			NotchAppleRecipes.INGOTS_PER_SLOT_WITH_GOLDEN_APPLE
		);
	}
}
