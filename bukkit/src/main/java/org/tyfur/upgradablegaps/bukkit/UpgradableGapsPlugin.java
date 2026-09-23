/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

package org.tyfur.upgradablegaps.bukkit;

import java.util.Iterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryType;
import org.bukkit.event.inventory.PrepareItemCraftEvent;
import org.bukkit.inventory.CraftingInventory;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.PlayerInventory;
import org.bukkit.inventory.Recipe;
import org.bukkit.inventory.ShapedRecipe;
import org.bukkit.plugin.java.JavaPlugin;

public final class UpgradableGapsPlugin extends JavaPlugin implements Listener {
    private static final int CENTER = 4;
    private static final int INGOTS_PER_SLOT = 8;
    private static final int OFFHAND_SLOT = 40;

    // Null before 1.13, when the enchanted apple was GOLDEN_APPLE with data 1.
    private final Material enchantedApple = Material.getMaterial("ENCHANTED_GOLDEN_APPLE");
    private boolean folia;
    private ShapedRecipe triggerRecipe;

    @Override
    public void onEnable() {
        folia = classExists("io.papermc.paper.threadedregions.RegionizedServer");
        // Before 1.12, PrepareItemCraftEvent only fires when some recipe matches the grid.
        if (!preparesEveryGrid()) {
            triggerRecipe = new ShapedRecipe(result()).shape("III", "IAI", "III");
            triggerRecipe.setIngredient('I', Material.GOLD_INGOT);
            triggerRecipe.setIngredient('A', Material.GOLDEN_APPLE, 0);
            getServer().addRecipe(triggerRecipe);
        }
        getServer().getPluginManager().registerEvents(this, this);
    }

    @Override
    public void onDisable() {
        if (triggerRecipe == null) {
            return;
        }
        for (Iterator<Recipe> it = getServer().recipeIterator(); it.hasNext(); ) {
            Recipe recipe = it.next();
            if (recipe instanceof ShapedRecipe && result().equals(recipe.getResult())
                    && ((ShapedRecipe) recipe).getIngredientMap().size() == 2) {
                it.remove();
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPrepare(PrepareItemCraftEvent event) {
        CraftingInventory grid = event.getInventory();
        if (grid.getType() != InventoryType.WORKBENCH) {
            return;
        }
        if (matches(grid.getMatrix())) {
            grid.setResult(result());
        } else if (triggerRecipe != null && arranged(grid.getMatrix(), 1)) {
            // The trigger recipe matched, but some slot holds fewer than 8 ingots.
            grid.setResult(null);
        }
    }

    // Vanilla must never handle taking this result: with no real recipe behind it,
    // Spigot copies the grid back after consuming one item per slot (a dupe).
    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onClick(InventoryClickEvent event) {
        Inventory top = event.getInventory();
        if (event.getRawSlot() != 0 || top.getType() != InventoryType.WORKBENCH || !(event.getWhoClicked() instanceof Player)) {
            return;
        }
        CraftingInventory grid = (CraftingInventory) top;
        if (!matches(grid.getMatrix())) {
            return;
        }
        event.setCancelled(true);
        Player player = (Player) event.getWhoClicked();
        craft(player, grid, event.getClick().name(), event.getHotbarButton());
        refresh(player);
    }

    private void craft(Player player, CraftingInventory grid, String click, int hotbarButton) {
        PlayerInventory inventory = player.getInventory();
        switch (click) {
            case "LEFT":
            case "RIGHT": {
                ItemStack cursor = player.getItemOnCursor();
                if (isEmpty(cursor)) {
                    player.setItemOnCursor(result());
                } else if (cursor.isSimilar(result()) && cursor.getAmount() < cursor.getMaxStackSize()) {
                    cursor.setAmount(cursor.getAmount() + 1);
                    player.setItemOnCursor(cursor);
                } else {
                    return;
                }
                consume(grid);
                break;
            }
            case "SHIFT_LEFT":
            case "SHIFT_RIGHT":
                while (matches(grid.getMatrix()) && inventory.addItem(result()).isEmpty()) {
                    consume(grid);
                }
                break;
            case "NUMBER_KEY":
                if (hotbarButton >= 0 && isEmpty(inventory.getItem(hotbarButton))) {
                    inventory.setItem(hotbarButton, result());
                    consume(grid);
                }
                break;
            case "SWAP_OFFHAND":
                if (isEmpty(inventory.getItem(OFFHAND_SLOT))) {
                    inventory.setItem(OFFHAND_SLOT, result());
                    consume(grid);
                }
                break;
            case "DROP":
                drop(player);
                consume(grid);
                break;
            case "CONTROL_DROP":
                while (matches(grid.getMatrix())) {
                    drop(player);
                    consume(grid);
                }
                break;
            default:
                break;
        }
    }

    private boolean matches(ItemStack[] matrix) {
        return arranged(matrix, INGOTS_PER_SLOT);
    }

    private boolean arranged(ItemStack[] matrix, int minIngots) {
        // Paper 1.8.8 hands back 10 slots here, the 9 grid slots plus a trailing null.
        if (matrix == null || matrix.length < 9) {
            return false;
        }
        for (int slot = 0; slot < 9; slot++) {
            ItemStack stack = matrix[slot];
            boolean ok = slot == CENTER
                    ? isGoldenApple(stack)
                    : stack != null && stack.getType() == Material.GOLD_INGOT && stack.getAmount() >= minIngots;
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    private void consume(CraftingInventory grid) {
        ItemStack[] matrix = grid.getMatrix();
        for (int slot = 0; slot < 9; slot++) {
            int take = slot == CENTER ? 1 : INGOTS_PER_SLOT;
            ItemStack stack = matrix[slot];
            if (stack.getAmount() > take) {
                stack = stack.clone();
                stack.setAmount(stack.getAmount() - take);
                matrix[slot] = stack;
            } else {
                matrix[slot] = null;
            }
        }
        grid.setMatrix(matrix);
    }

    private boolean isGoldenApple(ItemStack stack) {
        return stack != null && stack.getType() == Material.GOLDEN_APPLE && (enchantedApple != null || stack.getDurability() == 0);
    }

    @SuppressWarnings("deprecation")
    private ItemStack result() {
        return enchantedApple != null ? new ItemStack(enchantedApple) : new ItemStack(Material.GOLDEN_APPLE, 1, (short) 1);
    }

    private void drop(Player player) {
        Item item = player.getWorld().dropItem(player.getEyeLocation(), result());
        item.setVelocity(player.getEyeLocation().getDirection().multiply(0.3));
        item.setPickupDelay(40);
    }

    // The client predicted vanilla's one-per-slot craft; resend the real inventory.
    private void refresh(Player player) {
        player.updateInventory();
        if (!folia) {
            getServer().getScheduler().runTask(this, player::updateInventory);
        }
    }

    private static boolean isEmpty(ItemStack stack) {
        return stack == null || stack.getType() == Material.AIR || stack.getAmount() <= 0;
    }

    private static boolean preparesEveryGrid() {
        Matcher version = Pattern.compile("^(\\d+)\\.(\\d+)").matcher(Bukkit.getBukkitVersion());
        return !version.find() || Integer.parseInt(version.group(1)) > 1 || Integer.parseInt(version.group(2)) >= 12;
    }

    private static boolean classExists(String name) {
        try {
            Class.forName(name);
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }
}
