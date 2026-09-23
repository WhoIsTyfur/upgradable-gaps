/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.selftest;

import cpw.mods.fml.common.FMLLog;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLServerStartedEvent;
import cpw.mods.fml.common.network.NetworkMod;
import java.util.Arrays;
import net.minecraft.server.MinecraftServer;
import net.minecraft.src.ChunkCoordinates;
import net.minecraft.src.ContainerWorkbench;
import net.minecraft.src.EntityPlayer;
import net.minecraft.src.Item;
import net.minecraft.src.ItemStack;
import net.minecraft.src.World;

// Test-only: vanilla clients cannot join these servers, so craft through a real
// workbench menu on the server instead of with the bot.
@Mod(modid = "upgradablegaps_selftest", name = "Upgradable Gaps self-test", version = "test")
@NetworkMod(clientSideRequired = false, serverSideRequired = false)
public final class SelfTest {
    private static final int CENTER = 5;

    @Mod.ServerStarted
    public void started(FMLServerStartedEvent event) {
        World world = MinecraftServer.getServer().worldServerForDimension(0);
        // No FakePlayer before Forge 1.5.
        EntityPlayer player = new EntityPlayer(world) {
            public void sendChatToPlayer(String message) {
            }

            public boolean canCommandSenderUseCommand(String command) {
                return false;
            }

            public ChunkCoordinates getPlayerCoordinates() {
                return new ChunkCoordinates(0, 0, 0);
            }
        };
        StringBuilder failures = new StringBuilder();

        ContainerWorkbench menu = fill(player, Item.ingotGold, 8, Item.appleGold, 1);
        expect(failures, "upgrade result", isNotchApple(menu.getSlot(0).getStack(), 1));
        menu.slotClick(0, 0, false, player);
        expect(failures, "upgrade taken", isNotchApple(player.inventory.getItemStack(), 1));
        expect(failures, "upgrade grid emptied", gridEmpty(menu));
        player.inventory.setItemStack(null);

        menu = fill(player, Item.ingotGold, 16, Item.appleGold, 2);
        menu.slotClick(0, 0, true, player);
        expect(failures, "shift-click crafts twice", count(player, Item.appleGold, 1) == 2 && gridEmpty(menu));
        Arrays.fill(player.inventory.mainInventory, null);

        menu = fill(player, Item.ingotGold, 8, Item.appleGold, 1);
        menu.getSlot(1).putStack(new ItemStack(Item.ingotGold, 7));
        expect(failures, "seven ingots do nothing", menu.getSlot(0).getStack() == null);

        // Before 1.6 the golden apple takes gold nuggets.
        menu = fill(player, Item.goldNugget, 1, Item.appleRed, 1);
        ItemStack vanilla = menu.getSlot(0).getStack();
        expect(failures, "vanilla golden apple", vanilla != null && vanilla.getItem() == Item.appleGold && vanilla.getItemDamage() == 0);

        FMLLog.info("UPGRADABLEGAPS-SELFTEST %s", failures.length() == 0 ? "PASS" : "FAIL:" + failures);
    }

    private static ContainerWorkbench fill(EntityPlayer player, Item outer, int outerCount, Item center, int centerCount) {
        ContainerWorkbench menu = new ContainerWorkbench(player.inventory, player.worldObj, 0, 0, 0);
        for (int slot = 1; slot <= 9; slot++) {
            menu.getSlot(slot).putStack(slot == CENTER ? new ItemStack(center, centerCount, 0) : new ItemStack(outer, outerCount, 0));
        }
        return menu;
    }

    private static boolean isNotchApple(ItemStack stack, int count) {
        return stack != null && stack.getItem() == Item.appleGold && stack.getItemDamage() == 1 && stack.stackSize == count;
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
            if (stack != null && stack.getItem() == item && stack.getItemDamage() == damage) {
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
