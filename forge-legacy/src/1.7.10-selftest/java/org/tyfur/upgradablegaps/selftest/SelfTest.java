/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.selftest;

import com.mojang.authlib.GameProfile;
import cpw.mods.fml.common.FMLLog;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLServerStartedEvent;
import java.util.UUID;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.init.Items;
import net.minecraft.inventory.ContainerWorkbench;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.WorldServer;
import net.minecraftforge.common.util.FakePlayerFactory;

// Test-only: vanilla clients cannot join these servers, so craft through a real
// workbench menu on the server instead of with the bot.
@Mod(modid = "upgradablegaps_selftest", name = "Upgradable Gaps self-test", version = "test", acceptableRemoteVersions = "*")
public final class SelfTest {
    private static final int CENTER = 5;

    @Mod.EventHandler
    public void started(FMLServerStartedEvent event) throws ReflectiveOperationException {
        WorldServer world = MinecraftServer.getServer().worldServerForDimension(0);
        EntityPlayer player = FakePlayerFactory.get(world, profile());
        StringBuilder failures = new StringBuilder();

        ContainerWorkbench menu = fill(player, 8, 1, Items.golden_apple);
        expect(failures, "upgrade result", isNotchApple(menu.getSlot(0).getStack(), 1));
        menu.slotClick(0, 0, 0, player);
        expect(failures, "upgrade taken", isNotchApple(player.inventory.getItemStack(), 1));
        expect(failures, "upgrade grid emptied", gridEmpty(menu));
        player.inventory.setItemStack(null);

        menu = fill(player, 16, 2, Items.golden_apple);
        menu.slotClick(0, 0, 1, player);
        expect(failures, "shift-click crafts twice", count(player, Items.golden_apple, 1) == 2 && gridEmpty(menu));
        player.inventory.clearInventory(null, -1);

        menu = fill(player, 8, 1, Items.golden_apple);
        menu.getSlot(1).putStack(new ItemStack(Items.gold_ingot, 7));
        expect(failures, "seven ingots do nothing", menu.getSlot(0).getStack() == null);

        menu = fill(player, 1, 1, Items.apple);
        ItemStack vanilla = menu.getSlot(0).getStack();
        expect(failures, "vanilla golden apple", vanilla != null && vanilla.getItem() == Items.golden_apple && vanilla.getMetadata() == 0);

        FMLLog.info("UPGRADABLEGAPS-SELFTEST %s", failures.length() == 0 ? "PASS" : "FAIL:" + failures);
    }

    // The authlib in Forge 1.7.2 takes a String id, 1.7.10's a UUID.
    private static GameProfile profile() throws ReflectiveOperationException {
        try {
            return GameProfile.class.getConstructor(UUID.class, String.class).newInstance(UUID.randomUUID(), "selftest");
        } catch (NoSuchMethodException e) {
            return GameProfile.class.getConstructor(String.class, String.class).newInstance(UUID.randomUUID().toString(), "selftest");
        }
    }

    private static ContainerWorkbench fill(EntityPlayer player, int ingots, int centerCount, Item center) {
        ContainerWorkbench menu = new ContainerWorkbench(player.inventory, player.worldObj, 0, 0, 0);
        for (int slot = 1; slot <= 9; slot++) {
            menu.getSlot(slot).putStack(slot == CENTER ? new ItemStack(center, centerCount, 0) : new ItemStack(Items.gold_ingot, ingots));
        }
        return menu;
    }

    private static boolean isNotchApple(ItemStack stack, int count) {
        return stack != null && stack.getItem() == Items.golden_apple && stack.getMetadata() == 1 && stack.stackSize == count;
    }

    private static boolean gridEmpty(ContainerWorkbench menu) {
        for (int slot = 1; slot <= 9; slot++) {
            if (menu.getSlot(slot).getStack() != null) {
                return false;
            }
        }
        return true;
    }

    private static int count(EntityPlayer player, Item item, int damage) {
        int total = 0;
        for (ItemStack stack : player.inventory.mainInventory) {
            if (stack != null && stack.getItem() == item && stack.getMetadata() == damage) {
                total += stack.stackSize;
            }
        }
        return total;
    }

    private static void expect(StringBuilder failures, String name, boolean ok) {
        if (!ok) {
            failures.append(' ').append(name).append(';');
        }
    }
}
