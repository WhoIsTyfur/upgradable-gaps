// Copyright (c) 2026 Tyler Fursman
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

'use strict'

const mineflayer = require('mineflayer')
const { Vec3 } = require('vec3')

const [host, port, version, scenario, username] = process.argv.slice(2)
// The real server version; the bot may speak a newer protocol through ViaProxy.
const serverVersion = process.env.MCTEST_SERVER_VERSION || version

function serverBefore (other) {
  const a = serverVersion.split('.').map(Number)
  const b = other.split('.').map(Number)
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) < (b[i] || 0)
  }
  return false
}

// Before 1.7 /give only took numeric ids.
const NUMERIC_IDS = { gold_block: 41, crafting_table: 58, apple: 260, gold_ingot: 266, golden_apple: 322 }

const RESULT = 0
const CENTER = 5
const OUTER = [1, 2, 3, 4, 6, 7, 8, 9]
const GRID = [1, 2, 3, 4, 5, 6, 7, 8, 9]

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

async function waitFor (check, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const value = check()
    if (value) return value
    await sleep(50)
  }
  return check()
}

let bot

function connect () {
  return new Promise((resolve, reject) => {
    const client = mineflayer.createBot({ host, port: Number(port), username, version, auth: 'offline' })
    // ViaProxy mangles routine movement packets for some targets (26.3), and the
    // test never moves, so the harness can drop them. Teleport replies still go out.
    if (process.env.MCTEST_NO_MOVEMENT === '1') {
      const write = client._client.write.bind(client._client)
      client._client.write = (name, params) => {
        if (name === 'position' || name === 'look' || name === 'flying') return
        return write(name, params)
      }
    }
    client.once('spawn', () => resolve(client))
    client.once('kicked', reason => reject(new Error('kicked: ' + JSON.stringify(reason))))
    client.once('error', reject)
  })
}

// One login per step: before 1.17 the server never corrects slots it thinks the
// client already predicted, so only a fresh login shows the true inventory.
async function session (work) {
  bot = await connect()
  try {
    await sleep(1500)
    return await work()
  } finally {
    const ended = new Promise(resolve => bot.once('end', resolve))
    bot.quit()
    await Promise.race([ended, sleep(3000)])
    await sleep(500)
  }
}

const legacy = () => bot.registry.version['<']('1.13')

function isGoldenApple (item) {
  return !!item && item.name === 'golden_apple' && (!legacy() || item.metadata === 0)
}

function isEnchantedApple (item) {
  if (!item) return false
  return legacy() ? item.name === 'golden_apple' && item.metadata === 1 : item.name === 'enchanted_golden_apple'
}

function itemKey (item) {
  return legacy() ? `${item.name}@${item.metadata}` : item.name
}

const key = {
  enchanted: () => legacy() ? 'golden_apple@1' : 'enchanted_golden_apple',
  golden: () => legacy() ? 'golden_apple@0' : 'golden_apple',
  plain: name => legacy() ? `${name}@0` : name
}

function describe (window, slots) {
  return slots.map(slot => {
    const item = window.slots[slot]
    return item ? `${slot}:${itemKey(item)}x${item.count}` : `${slot}:-`
  })
}

function inventoryCounts () {
  const counts = {}
  for (const item of bot.inventory.items()) counts[itemKey(item)] = (counts[itemKey(item)] || 0) + item.count
  return counts
}

async function give (name, count) {
  const have = () => bot.inventory.items().filter(i => i.name === name).reduce((n, i) => n + i.count, 0)
  const before = have()
  // Before 1.8, /give throws the item where the player looks; aim at the feet to catch it.
  if (serverBefore('1.8')) {
    await bot.look(bot.entity.yaw, -Math.PI / 2, true)
    await sleep(400) // the look goes out on the next physics tick
  }
  if (serverBefore('1.7.2')) {
    bot.chat(`/give ${username} ${NUMERIC_IDS[name]} ${count} 0`)
  } else {
    bot.chat(legacy() ? `/give ${username} minecraft:${name} ${count} 0` : `/give ${username} minecraft:${name} ${count}`)
  }
  if (!await waitFor(() => have() >= before + count, 5000)) throw new Error(`/give ${name} ${count} did not arrive`)
}

// Players spawn near each other, so reuse a table another scenario left and
// try a few spots if the first is taken.
async function placeCraftingTable () {
  const base = bot.entity.position.floored()
  for (const [dx, dz] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) {
    const pos = base.offset(dx, 0, dz)
    const existing = bot.blockAt(pos)
    if (existing && existing.name === 'crafting_table') return existing
    if (serverBefore('1.7.2')) {
      // No /setblock yet: place a table by hand.
      if (!bot.inventory.items().some(i => i.name === 'crafting_table')) await give('crafting_table', 1)
      await bot.equip(bot.inventory.items().find(i => i.name === 'crafting_table'), 'hand')
      try {
        await bot.placeBlock(bot.blockAt(pos.offset(0, -1, 0)), new Vec3(0, 1, 0))
      } catch (err) {
        continue
      }
    } else {
      bot.chat(`/setblock ${pos.x} ${pos.y} ${pos.z} minecraft:crafting_table`)
    }
    const block = await waitFor(() => {
      const b = bot.blockAt(pos)
      return b && b.name === 'crafting_table' ? b : null
    }, 3000)
    if (block) return block
  }
  throw new Error('crafting table did not appear')
}

function findSlot (window, predicate) {
  for (let slot = window.inventoryStart; slot < window.inventoryEnd; slot++) {
    if (predicate(window.slots[slot])) return slot
  }
  return null
}

// Pick up a whole stack, right-click `perSlot` items into each slot, put the rest back.
async function place (window, predicate, slots, perSlot) {
  const source = findSlot(window, predicate)
  if (source === null) throw new Error('item to place is missing from the inventory')
  await bot.clickWindow(source, 0, 0)
  for (const slot of slots) {
    for (let i = 0; i < perSlot; i++) await bot.clickWindow(slot, 1, 0)
  }
  if (window.selectedItem) await bot.clickWindow(source, 0, 0)
}

// A plugin that cancels the click and crafts itself leaves some servers (1.12)
// without a click confirmation; the vanilla client ignores that, so the bot does too.
async function click (slot, button, mode) {
  try {
    await bot.clickWindow(slot, button, mode)
  } catch (err) {
    if (!/transaction/.test(String(err))) throw err
  }
}

async function takeResult (window, shift) {
  if (shift) {
    await click(RESULT, 0, 1)
  } else {
    await click(RESULT, 0, 0)
    await click(window.firstEmptyInventorySlot(), 0, 0)
  }
  await sleep(500)
}

// Each scenario logs in as a fresh player, so the inventory starts empty.
async function setUp (items) {
  const table = await placeCraftingTable()
  for (const [name, count] of items) await give(name, count)
  await bot.lookAt(table.position.offset(0.5, 0.5, 0.5), true)
  return bot.openBlock(table)
}

async function finish (window, checks, expected) {
  const grid = describe(window, [RESULT, ...GRID])
  // Before 1.12, closing the table throws the grid where the player looks instead of
  // returning it to the inventory; aim at the feet and wait out the pickup delay.
  if (serverBefore('1.12')) {
    await bot.look(bot.entity.yaw, -Math.PI / 2, true)
    await sleep(400)
  }
  bot.closeWindow(window)
  await sleep(serverBefore('1.12') ? 2500 : 500)
  return { checks, expected, grid }
}

const scenarios = {
  // Craftable Notch Apples: 8 gold blocks around an apple.
  async datapack () {
    const window = await setUp([['gold_block', 8], ['apple', 1]])
    await place(window, i => i && i.name === 'gold_block', OUTER, 1)
    await place(window, i => i && i.name === 'apple', [CENTER], 1)
    const shown = await waitFor(() => isEnchantedApple(window.slots[RESULT]), 3000)
    if (!shown) return finish(window, { resultShown: false }, {})
    await takeResult(window, false)
    return finish(window, { resultShown: true }, { [key.enchanted()]: 1 })
  },

  // Upgradable Gaps: 8 ingots in each outer slot around a golden apple.
  async upgrade () {
    const window = await setUp([['gold_ingot', 64], ['golden_apple', 1]])
    await place(window, i => i && i.name === 'gold_ingot', OUTER, 8)
    await place(window, isGoldenApple, [CENTER], 1)
    const shown = await waitFor(() => isEnchantedApple(window.slots[RESULT]), 3000)
    if (!shown) return finish(window, { resultShown: false }, {})
    await takeResult(window, false)
    return finish(window, { resultShown: true }, { [key.enchanted()]: 1 })
  },

  // Shift-click crafts one per golden apple and eats 8 ingots per slot each time.
  async upgradeBatch () {
    const window = await setUp([['gold_ingot', 64], ['gold_ingot', 64], ['golden_apple', 2]])
    await place(window, i => i && i.name === 'gold_ingot' && i.count === 64, OUTER.slice(0, 4), 16)
    await place(window, i => i && i.name === 'gold_ingot' && i.count === 64, OUTER.slice(4), 16)
    await place(window, isGoldenApple, [CENTER], 2)
    const shown = await waitFor(() => isEnchantedApple(window.slots[RESULT]), 3000)
    if (!shown) return finish(window, { resultShown: false }, {})
    await takeResult(window, true)
    return finish(window, { resultShown: true }, { [key.enchanted()]: 2 })
  },

  // One slot short: no result, and nothing may be consumed.
  async upgradeShort () {
    const window = await setUp([['gold_ingot', 63], ['golden_apple', 1]])
    await place(window, i => i && i.name === 'gold_ingot', OUTER.slice(0, 7), 8)
    await place(window, i => i && i.name === 'gold_ingot', [OUTER[7]], 7)
    await place(window, isGoldenApple, [CENTER], 1)
    await sleep(1500)
    return finish(window, { noResult: !window.slots[RESULT] }, { [key.plain('gold_ingot')]: 63, [key.golden()]: 1 })
  },

  // The vanilla golden apple recipe must keep working next to the upgrade.
  async vanillaGoldenApple () {
    if (serverBefore('1.6')) {
      return { skipped: 'before 1.6 the bot cannot take a result the server never announced' }
    }
    const window = await setUp([['gold_ingot', 8], ['apple', 1]])
    await place(window, i => i && i.name === 'gold_ingot', OUTER, 1)
    await place(window, i => i && i.name === 'apple', [CENTER], 1)
    // Before 1.12 the server never sends a real recipe's result; clients work it out
    // themselves, which the bot can't, so take it blind and trust the relog check.
    const shown = serverBefore('1.12') || await waitFor(() => isGoldenApple(window.slots[RESULT]), 3000)
    if (!shown) return finish(window, { resultShown: false }, {})
    await takeResult(window, false)
    return finish(window, { resultShown: true }, { [key.golden()]: 1 })
  }
}

function report (result) {
  console.log('RESULT ' + JSON.stringify(result))
}

async function main () {
  if (scenario === 'warmup') {
    // Only has to reach the server; whether it ever spawns does not matter.
    await Promise.race([session(async () => {}), sleep(15000)])
    return { ok: true }
  }
  if (!scenarios[scenario]) throw new Error(`unknown scenario ${scenario}`)
  const outcome = await session(() => scenarios[scenario]())
  if (outcome.skipped) return { ok: true, skipped: outcome.skipped }
  const inventory = await session(async () => inventoryCounts())
  const sorted = counts => JSON.stringify(Object.entries(counts).sort())
  const inventoryOk = sorted(inventory) === sorted(outcome.expected)
  const ok = inventoryOk && Object.values(outcome.checks).every(Boolean)
  return { ok, ...outcome.checks, inventoryOk, inventory, expected: outcome.expected, grid: outcome.grid }
}

const watchdog = setTimeout(() => {
  report({ ok: false, error: 'bot timed out' })
  process.exit(1)
}, 120000)

main()
  .then(report, err => report({ ok: false, error: String((err && err.stack) || err) }))
  .finally(() => {
    clearTimeout(watchdog)
    setTimeout(() => process.exit(0), 200)
  })
