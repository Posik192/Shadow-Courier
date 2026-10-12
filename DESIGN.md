# Shadow Courier - Game Design

## Name and genre
Shadow Courier is a 2D stealth puzzle game.

## Goal
The player must deliver a secret package to the exit without being caught by guards or staying too long in light zones.

## Controls
WASD - move  
Space - disable the nearest lamp  
E - interact with keys and doors  
P - pause  
Esc - menu  

## Core loop
The player enters a level, avoids lights and guards, collects keys or coins, disables lamps when needed, opens doors and reaches the exit. The reward is score points and access to the next level.

## Mechanics
1. Light danger: if the player stays inside a light zone for too long, the game ends.
2. Lamp shutdown: the player can disable a nearby lamp for a short time, but the ability has a cooldown.

## Levels
Level 1 is easy with one guard and a few lamps.  
Level 2 has more walls, guards and light zones.  
Level 3 is the hardest with more enemies, less safe space and faster guards.

## Scoring
Coins give 10 points.  
Keys give 25 points.  
Finishing a level gives 100 points.  
Finishing quickly gives bonus points.

## Save and load
The final score is sent to a server and saved in a database. The leaderboard shows the best scores.
