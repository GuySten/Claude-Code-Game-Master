---
name: gm-combat
description: D&D-kit combat mechanics — initiative, attack/damage resolution, XP-by-CR awards, combat modifiers, and death saves. Load when a hostile action is declared or combat starts in a campaign whose World Kit is dnd5e. For non-D&D kits, use the generic core (game_core.py) and the active ruleset instead.
---

# Combat Mechanics (D&D kit)

**STEP 0 — KIT GUARD.** If the scene-context KIT block is not `dnd5e`, close this skill and resolve the fight through the generic core (`game_core`) and the active ruleset.

**The referee resolves every roll** (`bash tools/gm-referee.sh`, lib/referee.py): numbers come
from the sheets and the foes' locked stat blocks, never from you, and every decision is logged.
`gm-combat.sh` keeps the turn order and conditions (`condition`, `next-turn`, `end`).

## Flow
1. Each foe: stat block from the `monster-manual` agent (`features/dnd-api/monsters/dnd_monster.py "[creature]" --combat`),
   as JSON `{"name", "ac", "hp", "abilities": {str..cha}, "skills", "saves", "passive_perception",
   "traits": [...], "temperament": "cowardly|cautious|brutal|cunning|fanatical",
   "attacks": [{"name", "to_hit", "damage": "1d6+2 slashing"} | {"name", "damage", "save": {"ability", "dc"}}]}`,
   locked in with `gm-referee.sh enemy '<json>'` (two of a kind: "Goblin 1", "Goblin 2").
2. `gm-referee.sh initiative` (everyone, from the records).
3. A PC's turn: `gm-referee.sh attack "<pc>" "<foe>" "<weapon on the sheet>"` (or a check, save,
   `hide`, `help`, `cover`). A foe's turn: spawn the **`combat-referee` agent** with the foe's
   name, and narrate the line it returns. `gm-combat.sh next-turn` between turns.
4. Resolution: `gm-combat.sh end`, award XP, handle loot (persist BEFORE narrating), advance time.

## XP by Challenge Rating
| CR | XP | CR | XP | CR | XP |
|----|-----|----|----|----|----|
| 0 | 10 | 4 | 1,100 | 10 | 5,900 |
| 1/8 | 25 | 5 | 1,800 | 11 | 7,200 |
| 1/4 | 50 | 6 | 2,300 | 13 | 10,000 |
| 1/2 | 100 | 7 | 2,900 | 15 | 13,000 |
| 1 | 200 | 8 | 3,900 | 17 | 18,000 |
| 2 | 450 | 9 | 5,000 | 20 | 25,000 |
| 3 | 700 | | | | |

Bonus: clever tactics +25%, creative environment +10-25%, social victory +50%.

**Non-kill wins still earn XP.** When a fight is won WITHOUT a kill — driving the enemy off a ledge, baiting two enemies into each other, an environmental kill, a daring escape from a lethal foe, surviving telegraphed over-CR odds — award it like a kill: `bash tools/gm-player.sh award --tier minor|major|legendary --reason "..."` (kit-aware, level-scaled; co-awards followers in DCC). See `gm-craft → Reward the spectacle`. Combat's CR→XP is just one source of XP among many.

## Modifiers (the referee applies these from recorded state, to both sides)
Advantage = 2d20 keep high; Disadvantage = keep low; both cancel. Half cover +2 AC (and DEX saves);
3/4 cover +5. Prone: advantage melee / disadvantage ranged; a prone attacker has disadvantage.
Blinded, frightened, poisoned, restrained attackers: disadvantage; attacks against blinded, paralyzed,
petrified, restrained, stunned, unconscious targets: advantage; melee hits on paralyzed or unconscious
targets are crits. Hidden (earned with `hide`) or invisible: advantage to attack, disadvantage to be
attacked. Crit (nat 20) = double damage dice then add mods. Nat 1 = auto-miss. No flanking (optional rule).
Hazards for everyone: `gm-referee.sh field "<name>" --effect dis:attack ...`.

## Death & Dying
0 HP → unconscious + death saves (`gm-referee.sh death-save "<pc>"`: a flat d20 vs 10 each turn): 3 successes = stable, 3 failures = death. Nat 20 = 1 HP + conscious. Nat 1 = 2 failures. Damage ≥ max HP = instant death.
Death is real and reachable — don't fudge saves to keep a doomed PC alive. Telegraph lethal fights first (an over-CR enemy should *read* as deadly), but once the player commits against the odds, let the dice fall. On PC death, run the **Death Protocol** (CLAUDE.md): persist → narrate → offer the character hand-off. The session does not end.
