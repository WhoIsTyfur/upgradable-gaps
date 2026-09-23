/*
 * Copyright (c) 2026 Tyler Fursman
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Same hooks as the Mixin builds, written against production (SRG) names. CLASS
// targets only: the coremods library in Forge 1.14.2 has no METHOD targets.
var Opcodes = Java.type('org.objectweb.asm.Opcodes');
var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');

var HOOKS = 'org/tyfur/upgradablegaps/forge/Hooks';
var SLOT = 'net/minecraft/inventory/container/CraftingResultSlot';
var GRID = 'Lnet/minecraft/inventory/CraftingInventory;';
var GRID_UPDATE = '(ILnet/minecraft/world/World;Lnet/minecraft/entity/player/PlayerEntity;' + GRID + 'Lnet/minecraft/inventory/CraftResultInventory;)V';

function method(classNode, name, desc) {
    for (var i = 0; i < classNode.methods.size(); i++) {
        var m = classNode.methods.get(i);
        if (m.name === name && m.desc === desc) {
            return m;
        }
    }
    throw 'upgradablegaps: ' + classNode.name + '.' + name + desc + ' not found';
}

function initializeCoreMod() {
    return {
        'upgradablegaps_grid': {
            'target': {'type': 'CLASS', 'name': 'net.minecraft.inventory.container.WorkbenchContainer'},
            'transformer': function (classNode) {
                var update = method(classNode, 'func_217066_a', GRID_UPDATE);
                var returns = [];
                for (var node = update.instructions.getFirst(); node !== null; node = node.getNext()) {
                    if (node.getOpcode() === Opcodes.RETURN) {
                        returns.push(node);
                    }
                }
                returns.forEach(function (ret) {
                    var call = new InsnList();
                    call.add(new VarInsnNode(Opcodes.ILOAD, 0));
                    for (var i = 1; i <= 4; i++) {
                        call.add(new VarInsnNode(Opcodes.ALOAD, i));
                    }
                    call.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOKS, 'showResult', GRID_UPDATE, false));
                    update.instructions.insertBefore(ret, call);
                });
                return classNode;
            }
        },
        'upgradablegaps_take': {
            'target': {'type': 'CLASS', 'name': 'net.minecraft.inventory.container.CraftingResultSlot'},
            // Take the upgrade and return before vanilla's remainder pass, which would
            // copy the grid back in (an item dupe) with no recipe matched.
            'transformer': function (classNode) {
                var onTake = method(classNode, 'func_190901_a',
                    '(Lnet/minecraft/entity/player/PlayerEntity;Lnet/minecraft/item/ItemStack;)Lnet/minecraft/item/ItemStack;');
                var vanilla = new LabelNode();
                var take = new InsnList();
                take.add(new VarInsnNode(Opcodes.ALOAD, 0));
                take.add(new FieldInsnNode(Opcodes.GETFIELD, SLOT, 'field_75239_a', GRID));
                take.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOKS, 'arranged', '(' + GRID + ')Z', false));
                take.add(new JumpInsnNode(Opcodes.IFEQ, vanilla));
                take.add(new VarInsnNode(Opcodes.ALOAD, 0));
                take.add(new VarInsnNode(Opcodes.ALOAD, 2));
                take.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, SLOT, 'func_75208_c', '(Lnet/minecraft/item/ItemStack;)V', false));
                take.add(new VarInsnNode(Opcodes.ALOAD, 0));
                take.add(new FieldInsnNode(Opcodes.GETFIELD, SLOT, 'field_75239_a', GRID));
                take.add(new MethodInsnNode(Opcodes.INVOKESTATIC, HOOKS, 'consume', '(' + GRID + ')V', false));
                take.add(new VarInsnNode(Opcodes.ALOAD, 2));
                take.add(new InsnNode(Opcodes.ARETURN));
                take.add(vanilla);
                onTake.instructions.insert(take);
                return classNode;
            }
        }
    };
}
