/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.registry.GameRegistry;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.ContainerWorkbench;
import net.minecraft.item.ItemStack;
import net.minecraft.network.play.server.S2FPacketSetSlot;

@Mod(modid = "upgradablegaps", name = "Upgradable Gaps", acceptableRemoteVersions = "*")
public final class UpgradableGapsForge {
    private final Map<EntityPlayerMP, Shown> shown = new WeakHashMap<EntityPlayerMP, Shown>();

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        GameRegistry.addRecipe(new UpgradeRecipe());
        FMLCommonHandler.instance().bus().register(this);
    }

    // Fires before vanilla removes one item from each slot; take the other seven.
    @SubscribeEvent
    public void onCrafted(PlayerEvent.ItemCraftedEvent event) {
        if (UpgradeRecipe.arranged(event.craftMatrix)) {
            UpgradeRecipe.takeExtraIngots(event.craftMatrix);
        }
    }

    // These servers never send the crafting result slot; vanilla clients work it
    // out themselves, which they can't for this recipe.
    @SubscribeEvent
    public void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.player instanceof EntityPlayerMP)
                || !(event.player.openContainer instanceof ContainerWorkbench)) {
            return;
        }
        EntityPlayerMP player = (EntityPlayerMP) event.player;
        Container menu = player.openContainer;
        ItemStack result = menu.getSlot(0).getStack();
        Shown last = shown.get(player);
        if (last == null || last.windowId != menu.windowId || !ItemStack.areItemStacksEqual(last.stack, result)) {
            player.playerNetServerHandler.sendPacket(new S2FPacketSetSlot(menu.windowId, 0, result));
            shown.put(player, new Shown(menu.windowId, result == null ? null : result.copy()));
        }
    }

    private static final class Shown {
        final int windowId;
        final ItemStack stack;

        Shown(int windowId, ItemStack stack) {
            this.windowId = windowId;
            this.stack = stack;
        }
    }
}
