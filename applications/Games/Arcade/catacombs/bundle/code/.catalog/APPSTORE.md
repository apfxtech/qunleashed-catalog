# Catacombs of the Damned!

A first-person dungeon crawler, drawn in real time on the 128x64 one-bit screen. Descend ten floors of a procedurally generated catacomb, burn skeletons, mages, bats and spiders with magical fireballs, pry open chests and try to reach the last exit alive.

This is a port, not an original game. **Catacombs of the Damned!** was written by **James Howard** for the Arduboy as [Arduboy3D](https://github.com/jhhoward/Arduboy3D), and is itself an homage to the classic *Catacomb 3-D*. This build carries it over to the Flipper Zero: the Arduino layer is gone and the engine talks to the Flipper API directly, rendering into the firmware's own canvas buffer, saving to the SD card, and wrapped in a native menu with a title screen, a high score, and sound and backlight toggles.

## The dungeon

Every floor is generated from scratch when you enter it: a 32x24 grid of brick is split recursively into rooms, doorways are knocked through the shared walls, and any hall that comes out too open gets a block of masonry dropped in the middle of it. Torches light the walls, urns block the corners, and the entrance and the exit sit at opposite ends of the map.

Then it is populated: up to 24 monsters, all placed out of line of sight of where you start, and eight pieces of treasure kept clear of both stairs — a healing potion, gold coins, a chest, a crown or a scroll, rolled one by one.

There are ten floors. Step onto the exit and the next one is built; step onto the exit of the tenth and you have escaped the catacombs.

## Gameplay

- 100 health and 100 mana. A fireball costs 20 mana and deals 10 damage, and mana trickles back a point at a time while you are not reloading — five shots, then a pause.
- Health never regenerates on its own and carries from floor to floor. Mana refills at every descent; hit points do not. A potion restores 25, and is only spent if you are actually hurt.
- **Skeleton knight** - 50 health, slow, hits for 20, staggers when hit.
- **Mage** - 30 health, ranged, hits for 20, fires back down any open corridor.
- **Bat** - 20 health, fast, hits for 10, never flinches.
- **Spider** - 10 health, fast, hits for 5, dies to one fireball but comes in numbers.
- Loot is scored: 15 per chest, 10 per crown, 8 per scroll, 4 per coin pile, plus 20 per floor cleared and 500 for escaping the tenth. Kills score 10 for a skeleton or a mage, 5 for a bat, 4 for a spider.
- The run is scored whether you died or escaped, broken down by loot and kills, and the best result is kept on the SD card.

## Controls

In the dungeon:

- **Up / Down** - walk forward / backward
- **Left / Right** - turn
- **OK** - cast a fireball
- **OK + Left / Right** - strafe
- **Back long** - back to the menu

Walking into a chest opens it, walking over an item picks it up, and walking onto the exit takes you down a floor.

In the menu the arrows move and OK confirms. **Play** starts a run, **Sound** and **Light** toggle the speaker and the backlight, **Score** and **High** show your last and best runs, and **Credits** replays the title screen. A long press of Back leaves the app.
