/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.forge;

import cpw.mods.fml.common.ICraftingHandler;
import cpw.mods.fml.common.ITickHandler;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.TickType;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.network.NetworkMod;
import cpw.mods.fml.common.registry.GameRegistry;
import cpw.mods.fml.common.registry.TickRegistry;
import cpw.mods.fml.relauncher.Side;
import java.util.EnumSet;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.ContainerWorkbench;
import net.minecraft.inventory.IInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.network.packet.Packet103SetSlot;

@Mod(modid = "upgradablegaps", name = "Upgradable Gaps")
@NetworkMod(clientSideRequired = false, serverSideRequired = false)
public final class UpgradableGapsForge implements ICraftingHandler, ITickHandler {
    private final Map<EntityPlayerMP, Shown> shown = new WeakHashMap<EntityPlayerMP, Shown>();

    @Mod.Init
    public void init(FMLInitializationEvent event) {
        GameRegistry.addRecipe(new UpgradeRecipe());
        GameRegistry.registerCraftingHandler(this);
        TickRegistry.registerTickHandler(this, Side.SERVER);
    }

    // Runs before vanilla removes one item from each slot; take the other seven.
    @Override
    public void onCrafting(EntityPlayer player, ItemStack item, IInventory craftMatrix) {
        if (UpgradeRecipe.arranged(craftMatrix)) {
            UpgradeRecipe.takeExtraIngots(craftMatrix);
        }
    }

    @Override
    public void onSmelting(EntityPlayer player, ItemStack item) {
    }

    @Override
    public void tickStart(EnumSet<TickType> type, Object... tickData) {
    }

    // These servers never send the crafting result slot; vanilla clients work it
    // out themselves, which they can't for this recipe.
    @Override
    public void tickEnd(EnumSet<TickType> type, Object... tickData) {
        if (!(tickData[0] instanceof EntityPlayerMP)) {
            return;
        }
        EntityPlayerMP player = (EntityPlayerMP) tickData[0];
        if (!(player.openContainer instanceof ContainerWorkbench)) {
            return;
        }
        Container menu = player.openContainer;
        ItemStack result = menu.getSlot(0).getStack();
        Shown last = shown.get(player);
        if (last == null || last.windowId != menu.windowId || !ItemStack.areItemStacksEqual(last.stack, result)) {
            player.playerNetServerHandler.sendPacketToPlayer(new Packet103SetSlot(menu.windowId, 0, result));
            shown.put(player, new Shown(menu.windowId, result == null ? null : result.copy()));
        }
    }

    @Override
    public EnumSet<TickType> ticks() {
        return EnumSet.of(TickType.PLAYER);
    }

    @Override
    public String getLabel() {
        return "upgradablegaps";
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
