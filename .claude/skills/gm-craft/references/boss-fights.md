# Boss fights: stages, fairness, drama

A named boss is the campaign's set piece: prepared as a short play in stages, fair
because every change is planned, visible and announced, and scored so the music
follows the stages (`orchestrate/references/boss-music.md`). Ordinary fights need
none of this. Numbers refer to `design-directives.md`; sources at the end.

## Before the session: the stage plan

1. **Write the stages in prep, never mid-fight.** Default three stages for an arc
   boss, two for a lieutenant. For each: its numbers (a stat block or a hit-point
   pool), the **trigger**, what changes, how it shows, and its music cue. No new
   stage and no new numbers are invented at the table (34, T2). [Angry GM; Giffyglyph; Theros mythic]
2. **Triggers the players can see.** Bloodied (half hit points: a public state in
   the 2024 rules that does nothing by itself), a fixed share of hit points (two
   thirds, one third), an announced round clock (`gm-clock.sh`), or a party action
   (the chain broken, the idol smashed). Never a secret condition. [SRD 5.2; Giffyglyph; 13th Age; Draw Steel]
3. **Foreshadow that it has stages.** Lore, a rumour, a knowledge check, an earlier
   meeting or the villain's boast tells the table it will not fall at the first
   wound and roughly how long the fight may run. A boss that rises again at 0 hit
   points without this warning is a cheat. (V4) [Angry GM; Theros; Stout]
4. **Two or three rounds a stage, five to eight in all.** Size each stage's hit
   points to the party's damage a round. [Angry GM; Sly Flourish]
5. **Each stage asks for a different answer.** New movement, range, objective or
   terrain so the last stage's winning tactic stops working; some powers stay. Later
   stages remove defences rather than add them, and the last should feel winnable:
   the boss desperate, dangerous, beatable. [Angry GM; 13th Age]

## The action economy

6. **A lone boss loses to the party's five turns to one, and to a single stun** - with a
   party. With ONE player there is no such imbalance: drop the fixes below to at most one
   villain action and one priced Legendary Resistance, and size each stage to the PC's
   damage a round (`prep-checklist.md`, "One player"). Fix
   it in prep: legendary actions (SRD: usually three, regained at the start of its
   turn, one after another creature's turn, none while Incapacitated), Legendary
   Resistance, or villain actions (three per fight, at most one a round, at the end
   of another creature's turn: an opener in round 1-2, crowd control in round 2-3,
   the ultimate in round 3-4 - never the ultimate first). [SRD 5.2; MCDM / Draw Steel; Sly Flourish]
7. **Never alone without a reason.** Minions, a bodyguard, a lieutenant that draws
   control spells, an active hazard; or, truly alone, extra turns (two initiative
   slots, or a turn per remaining pool). [Sly Flourish; Angry GM; 4e solos via Chris Sims]
8. **Plan how it sheds being stunned or held**, and say so when it does: Legendary
   Resistance, conditions ending at each stage change, a visible price paid to break
   free. [SRD 5.2; Angry GM; MCDM]

## In the fight: fair and readable

9. **Telegraph the big attack a full turn ahead.** End the boss's turn with the
   wind-up of its next signature move (the breath gathering, sigils igniting), so the
   players can scatter, shield or interrupt - and let a good counter work. The same
   tell always means the same attack, and how dangerous it looks is how dangerous it
   is. No unannounced one-shot kills. (9, 15; V4) [Angry GM; video-game boss design]
10. **Report its state every round.** Bloodied said aloud, wounds scaled to its size,
    morale shown through behaviour. The players can always judge how much fight is
    left. (16; V4) [SRD 5.2; Angry GM]
11. **A stage change is a short, announced scene.** Narrate it (the armour splits, the
    floor gives way, the flame takes her), state plainly what is new in the rules and
    that conditions on the boss have ended, roll its new initiative if the plan says
    so, then play on. Nobody is hurt during the change itself. Switch the music on the
    narration: `gm-table.sh music boss "<boss>" stage 2 --via break` (a transformation)
    or `--via rise` (an escalation); `... hit` for a decisive blow; `... end victory|requiem|escape|wipe`
    when it falls, yields, flees or the party falls (`boss-music.md`). [Giffyglyph; Angry GM]
12. **No secret numbers, ever.** No hidden hit-point changes, damage bumps or new
    resistances - even where Sly Flourish or Draw Steel suggest a dial. A fight that
    goes too easy or too hard moves only by planned, visible levers: announced
    reinforcements on a known clock, the next written stage, a weakness revealed, the
    villain's will visibly breaking. (34, T2; V3) [this repo's rule overrides those sources]
13. **It learns only where the table can see it.** It switches targets, shouts orders,
    avoids what hurt it - all described; it never silently gains an immunity. An
    escaped villain may return with a foreshadowed upgrade. [Angry GM; 13th Age]

## Drama

14. **Give it a voice.** A line or two most rounds, aimed at particular PCs; short, so
    play doesn't stall. Its barks can telegraph its plans. [Sly Flourish; Angry GM; Draw Steel]
15. **Its temperament chooses its tactics.** Confident, enraged, desperate - decide one
    per stage, and let it pick targets and risks to match, not only the best play.
16. **The battlefield changes.** At least one stage alters the terrain in a way the
    party can use or must answer; cover, height and things to interact with. (14, 73)
17. **Every PC matters.** Before the fight, check that each PC has a real role in at
    least two stages; spread its attacks and control effects; never keep one PC out of
    action for several rounds. (38, 41; V3)
18. **Several endings, chosen by play.** Prepare death, surrender (and what it
    offers), escape (its route and its oath) and, where the story fits, transformation
    or redemption. Don't rig its survival. An intelligent boss reaches a morale point
    near its last stage: it fights on, flees, bargains or betrays - shown in its
    behaviour first, and said plainly if it will return. [The Alexandrian; Angry GM; Draw Steel]
19. **Retreat is real.** The party can flee, at a cost the story names, so a losing
    fight need not end in a wipe. (46) [13th Age; Draw Steel]
20. **Close on the payoff.** When it falls, yields or flees: the decisive player
    describes the blow, the fight's story question is answered, and the music ends
    as the ending deserves (a victory tag, a requiem for a tragic foe, an unresolved
    break for an escape). (37, 66) [Stout; Draw Steel]

## Sources

Angry GM, boss-fight and solo-monster articles (theangrygm.com); Sly Flourish
(slyflourish.com: boss fights, action-oriented monsters, tuning solos); MCDM / Matt
Colville, villain actions (Draw Steel rules; MCDM's 5e books); Giffyglyph's Monster
Maker (phases at two thirds and one third); D&D *Mythic Odysseys of Theros*, mythic
monsters (via Wizards' D&D Beyond announcement); D&D 4e solos and bloodied (via Chris
Sims, Critical Hits); 13th Age escalation die; Mike Stout, boss-battle structure
(video-game design); The Alexandrian on villains. System Reference Document 5.2.1 by
Wizards of the Coast (CC BY 4.0): Bloodied, legendary actions, Legendary Resistance.
Research notes with URLs: private campaigns repo, `research/gm-design/src-bosses.md`.
