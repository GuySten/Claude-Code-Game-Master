# Design directives for the GM

A working set of rules for running a group at the online table, merged from GM craft
essays, game-design theory and open game texts, and checked against the host's verdicts from
real play. gm-craft SKILL.md stays the source of truth: where a directive restates it, it says
so (= *Section*). Companions: `prep-checklist.md`, `play-card.md`, `session-review.md`.

**Host verdicts** (each fixed in SKILL.md; never contradict them):
V1 tie the party together · V2 many clues, free, spread across the party · V3 fairness is
consistency plus balance over time, not equal counts · V4 decisions need information (e.g. an
enemy's strength) · V5 keep a map · V6 tell every money and item change.

**Source tags.** *Laws p.N*: Robin's Laws of Good Game Mastering. *Schell L#N / ch.N*: The Art
of Game Design, 3rd ed. (lens / chapter). *S&Z ch.N*: Salen & Zimmerman, Rules of Play.
*Alexandrian, Angry GM, Sly Flourish, Gnome Stew, Colville, Baker*: GM essays. *Meier, MDA, Chen
(flow), Koster, SDT, Booth (L4D director), Hitchcock, Loewenstein, Lazzaro, QF (Quantic
Foundry)*: design theory. *DW, AW, Blades, Fate, Ironsworn, D&D SRD 5.2, Lazy GM RD, GUMSHOE*:
open game texts (SRDs; Apocalypse World via its free reference sheet).

---

## 1. Party glue and shared goals

1. **Tie every PC to another PC before the first scene.** One relationship question per player
   (or proposed ties they accept or change); one follow-up; record with `gm-note.sh npc_relations
   "Bond: …"`. The answers are hooks. = *Openings*. [DW SRD bonds; AW Hx; Fate phase trio; Lazy GM RD; Laws p.15] V1
2. **Give the party one shared stake with a named goal and a visible finish line.** Say it as a
   verb plus obstacle; players must be able to tell when they've won. Check PC concepts against
   it at creation. [Laws pp.15-16; Schell L#32; S&Z ch.7, ch.20] V1
3. **Open with all the PCs in one scene, facing one problem none of them can solve alone.**
   Introduce each through what they do there, never as a roll call. = *Openings*. [Sly Flourish; DW first session; Colville; Schell L#44] V1
4. **Build obstacles that need two PCs' abilities combined.** One holds the door while another
   breaks the ward; one reads the rune, another knows the place it names. Note in prep which PCs
   each obstacle links. [S&Z ch.4, ch.14; Schell L#44, ch.25] V1 V2
5. **Put a pressure on the party that only the party together can push back.** A threat that
   keeps advancing (`gm-clock.sh add … --consequence`) makes cooperation the situation's demand,
   not the GM's plea. [S&Z ch.2 (Knizia), ch.27; DW fronts] V1
6. **Give the party something in common to protect.** A haven with healing and advice, a patron
   or contact who brings leads when they stall, a shared name or property. [Laws p.15; Schell ch.25; Lazy GM RD] V1
7. **Keep the glue alive in play.** NPCs address the party as a group; after an intense scene
   leave a short beat for PCs to talk to each other; when a PC drifts off, bring one of their
   bonds into the scene instead of scolding. = *Openings*. [Schell L#96; Laws p.26; Lazy GM RD campsite stories] V1

## 2. Information and meaningful decisions

8. **Before any real choice, give what the characters could reasonably know.** The threat in
   plain words, the stakes aloud, a way out; a size-up gets an honest tier. Never hold back
   numbers, maps or stakes "for immersion": players are immersed in their choices, and clarity
   is part of that. = *Decisions need information*. [Meier GDC 2012; Schell L#35; S&Z ch.15, ch.27; Laws p.13] V4
9. **Warn before you hurt: sound, then sight, then contact.** A soft move (signs of a threat)
   comes before a hard one (damage, loss); harm only as the fiction has already shown possible.
   How dangerous a thing looks must match how dangerous it is. [DW SRD soft/hard moves; AW; S&Z ch.26; Angry GM] V4
10. **Before a risky roll, pin down the goal, say what it can cost, then ask if they still do it.**
    Ask what they want from it if that's unclear; name the danger and the kind of consequence ("if
    this goes wrong, the patrol hears you"); let them change approach. The exact twist may stay
    open. See T3. [Blades SRD action roll, position & effect; DW; Angry GM; Alexandrian] V4 V3
11. **Make every offered choice a real one.** If one option always wins, or picking at random
    does as well, change the options or narrate past the moment. Keep a safe, modest path beside a
    risky, rich one, with reward in proportion to risk; keep short, session and campaign goals
    live at once. [Meier GDC 2012; Schell L#39, L#40; S&Z ch.6] V4
12. **Use the action menu to steer without closing doors.** With the menu ON, the three options
    are concrete openings from the fiction, ideally each suited to a different PC, and "Or
    something else..." stays true. Never a blank page, never a hidden right answer. [Schell ch.18, L#79; DW] V1 V4
13. **Answer factual questions truthfully; roll only for how much more.** What a character could
    perceive or know, they get without a roll. NPCs may lie; the narrator never does. [AW "always say"; Blades gathering information; GUMSHOE] V4 V2
14. **Describe what can be used, and say what terrain does.** A vividly described chandelier or
    nervous guard is an invitation: support it, or describe it less. Cover, difficult ground and
    blocked sight are stated before anyone moves. [Schell L#30, ch.18; S&Z ch.27 (field of battle)] V4 V5
15. **Give each foe type a few behaviour rules and play them the same way every time.** Does it
    warn before attacking, flee when bloodied, guard its leader? Observed habits let players judge
    it. [S&Z ch.27 (procedural characters); Ironsworn SRD NPCs; level-design legibility] V4
16. **Show the state of a fight every round.** Health labels (Healthy, Wounded, Bloodied,
    Critical), how the enemy's nerve holds, and every few rounds a two-line summary of threats and
    openings. [CLAUDE.md output; S&Z ch.25; Angry GM] V4
17. **Before a hard set-piece, give a planning glimpse.** A scout's report, an overheard order,
    the view from the ridge, so resources are spent knowingly. [S&Z ch.26, ch.2] V4
18. **When the table is stuck on a misreading, say so plainly, out of character.** One clear line
    beats in-fiction hints that get explained away. If they acted on a real misunderstanding of
    your description, rewind to that point; if an action can't work, `gm-table.sh redo` says why
    before any roll. [Laws pp.27, 29; GUMSHOE] V4 V3

## 3. Clues and mysteries

19. **Three clues per conclusion, by different routes.** A thing, a person, a place; different
    skills and senses. Keep a revelation list: conclusion → clues → who could find each. = *Clues*.
    [Alexandrian Three Clue Rule; S&Z ch.16 (redundancy); Schell L#56] V2
20. **Core clues are free.** Looking in the right place with a fitting skill finds it; rolls
    decide extras, speed and cost. Never make an obscure skill the only route. = *Clues*. [GUMSHOE core clues; Lazy GM RD] V2
21. **Spread the routes across the PCs.** Each PC gets a route that fits them; mark who has had
    none yet and aim the next one there. = *Clues*. [Schell L#56; S&Z ch.33; Laws p.20] V2 V3
22. **Narrate a found clue to the whole table, finder in the spotlight.** `say`, not `--to`,
    unless the secret itself is the point (T6). = *Clues*. [S&Z ch.17, ch.26] V2 V3
23. **Fix the truth before play and never move it.** Each clue narrows the answer; shifting the
    solution to match or dodge guesses makes every clue worthless. [S&Z ch.16 (Mastermind)] V2 V3
24. **Keep about ten untethered secrets per session; drop each wherever the PCs actually look.**
    Sensible unplanned methods earn real information; unused secrets carry forward. [Lazy GM RD; Sly Flourish; Alexandrian] V2
25. **Build investigations as a web, not a chain.** Each place or person points to several others
    (and back); any order works; a core clue can move into an improvised scene. [Alexandrian node design; GUMSHOE; Laws p.20] V2
26. **When the party stalls, bring a lead to them.** The villain acts, a witness comes forward,
    a patron sends word. Release held-back leads on frustration, not on a schedule. [Alexandrian proactive clues; GUMSHOE floating clues; Fate] V2
27. **Every search moves the story.** Strong result: the next step is clear. Partial: useful
    information plus a new problem. Failure: a threat or an unwelcome truth, never "nothing".
    [Ironsworn SRD gather information; DW SRD] V2
28. **Keep what the party knows shared and current.** When play resumes and after a breakthrough,
    a short `say` lists what is known and what is still open; confirm partial deductions as they
    happen. Public clues are also what each player's Narrator tab can recall. [S&Z ch.17; Schell L#55] V2
29. **No planted red herrings, no real-world trivia gates.** Players invent their own false
    leads; a riddle that needs outside knowledge favours one player. Puzzles get an obvious goal,
    visible progress, a parallel track, hints, and the answer when the table is truly stuck.
    [Alexandrian; Laws p.16; S&Z ch.27; Schell ch.14] V2 V3

## 4. Fairness, consistency and balance over time

30. **Same task, same conditions, same DC.** Choose the ladder word from the task and the fiction
    before the roll (`gm-referee.sh check "<PC>" <skill> --dc medium`), never from who rolls; a
    different DC needs its reason shown first. = *Fairness*. [S&Z ch.11; Schell L#25, L#92; Laws p.9; Sly Flourish] V3
31. **Make a ruling once, tell everyone, log it.** A new call on how something works goes to the
    whole table and into `gm-note.sh rules "<ruling and why>"`, and is reused. Never penalise a
    ruling the table hadn't heard. [S&Z ch.11, ch.28; Schell L#33; Laws p.29] V3
32. **Roll in the open; keep the trail checkable.** The table shows every roll with its DC;
    `--secret` only for an NPC roll whose result the PCs couldn't know (T1). `gm-referee.sh
    log`/`report` let anyone audit. [S&Z ch.8 (black box); Schell L#95½; Alexandrian] V3
33. **Never fudge, and never stack rolls to block an outcome.** If you can't accept a result,
    don't roll. One action, one roll; no re-roll without a new approach or a rule that grants one.
    [Alexandrian; Angry GM; Blades; CLAUDE.md Dice] V3
34. **Fix a mis-tuned fight only through the fiction, the same for everyone.** Foes flee, surrender
    or call help; the floor shakes for all (`gm-referee.sh field`). Never touch locked stat blocks
    or PC numbers (T2). [S&Z ch.18; Schell ch.13; D&D SRD 5.2 troubleshooting] V3
35. **Rule disputes: listen, rule, move on.** Answer a private challenge honestly and rule in
    public; revise an interpretation only going forward, never a past outcome. = *Fairness*. [Laws p.29; Fate "chairman, not god"] V3
36. **Information about a PC goes to that PC.** Never tell one player a secret about another's
    character, unless that character would hide it; then the hiding is the story. = *Fairness*.
    [Laws p.31; Schell L#29; S&Z ch.17] V3
37. **Name every contribution that mattered.** A group win credits each part by PC name, along
    several lines (who scouted, who held, who talked); a decisive move gets its moment without
    erasing the rest. = *Fairness*. [Schell ch.9; S&Z ch.20 (Gauntlet); Laws p.20] V3
38. **Balance spotlight and rewards over the session and the arc, weighted by appetite.** Not
    equal counts: a scene may rightly belong to one PC, and a player who likes the background
    wants less. Keep the per-PC ledger (`session-review.md`). [Laws pp.26, 30, 32; Schell L#37; S&Z ch.20] V3
39. **Counter the spotlight's snowball.** Whoever acts gets more scene, clues and openings. After
    a big moment, aim the next hook or threat at the PC with the least recent spotlight (unless
    they prefer the background). This includes `--heroic` beats and `grow` moments. [S&Z ch.18 (feedback loops); Laws pp.30-31] V3
40. **Keep world logic consistent; give exceptions a visible tell.** The same-looking door, rune
    or creature behaves the same; something different looks different before it bites. [S&Z ch.25; Schell ch.17] V3 V4
41. **No pile-ons, no sitting out.** Foes don't hunt the weakest PC out of play without a reason
    in the fiction; a downed or absent PC's player still gets something to decide or see (after one
    round down: a death's-door scene, an ally NPC to voice, or a choice; CLAUDE.md Multiplayer). [S&Z ch.28, Caribbean Star notes; Dungeon World "Last Breath"] V3

## 5. Challenge, difficulty and danger

42. **Size fights with the SRD budget, then let the fiction show the size.** Low, moderate or
    high by XP per PC; a fight that may kill reads as deadly and has an exit. [D&D SRD 5.2 encounter difficulty; Lazy GM RD deadly check; CLAUDE.md Stakes] V4
43. **Let players choose their difficulty through the fiction.** The guarded gate or the sewer,
    the truce or the assault, each readable. Prefer this to quiet adjustment: it keeps their
    sense of control. [Chen; SDT; Schell ch.13] V4
44. **Ramp in a sawtooth; teach a danger before it matters.** Climb, let them breathe, climb
    higher. Show a new trap or monster trick at low stakes first; when a tactic turns routine,
    change the terrain, objective or enemy mix. [Schell ch.10, L#21; Koster; kishotenketsu (Hayashida); Angry GM]
45. **Make fights about more than hit points.** Mixed foe roles, terrain with reasons to move, an
    unusual element in every long fight; fights end in rout, surrender, capture or retreat as often
    as in death. [D&D SRD 5.2; Laws p.28; S&Z ch.27]
46. **Make retreat a real option.** When the party flees, let them confer and each move before
    pursuit; pursuit follows the foe's motive. [Angry GM] V4
47. **After a serious setback, make sure they know why.** In the fiction, or one line out of it.
    A punishment that couldn't be foreseen or avoided reads as unfair. [Meier GDC 2010; Schell L#47] V3 V4
48. **Prefer a ticking clock to a blow from nowhere; never let a complication cancel a success.**
    Trouble that builds (`gm-clock.sh advance`) is fair; if the roll cornered the foe, he stays
    cornered and the cost lands elsewhere. When the fiction outruns a clock, set it to match and say
    so. [Blades SRD clocks, consequences] V3

## 6. Spotlight and the players' kinds of fun

49. **Keep a play-preference note per PC, from what you observe.** What lights them up: fights,
    tactics, a signature move, character drama, story momentum, discovery, loot, or just being
    there. Working guesses, revised each session; in-game behaviour only, filed under the PC's
    name. A player who prefers the background stays there. [Laws pp.3-6, 30; Schell L#19-20; MDA; QF; Lazzaro] V3
50. **Audit each session for every player's kind of fun, and patch only the gaps.** A fight worth
    winning, a logical problem, the signature-move scene, a dilemma, a subplot step, a usable
    reward: one beat per player who wants one. [Laws pp.6, 21-22] V3
51. **Give every player a beat before the scene moves on, and the quiet one a named, concrete
    prompt.** Address characters by name, with something that suits them. = CLAUDE.md
    *Spotlight*. [DW "address the characters"; Gnome Stew; Fate Condensed] V3
52. **Design for the watchers.** At this table whoever isn't acting is watching: short beats, cuts
    at tension, something to react to. When the party splits, alternate short beats and cut on
    small cliffhangers. [Schell L#95; Gnome Stew; Laws p.31] V3
53. **Be a fan of the characters.** Make them look competent; a bad start shows a capable enemy,
    not clumsy heroes; their wins change the world. A fan is not a softie (T9). [DW; Blades; Lazy GM RD]
54. **Read the table in text.** Reply length and speed, jokes, in-character banter, requests to
    repeat. When several fade, change focus now (serve the most players, or the least happy one).
    If the trouble is outside the game, tell the host and suggest a pause. [Laws pp.25-26; Schell ch.1]

## 7. Pacing and session structure

55. **Start strong, end high.** Open on a development that demands a decision within minutes;
    plan back so the biggest moment lands last; end on a hook (`gm-session.sh end …
    --cliffhanger`). = *Pacing*. [Lazy GM RD; Schell L#69; Laws p.32; Meier]
56. **Resume with a recap and the goals.** Ask a player for the recap, fill the gaps, then one
    line: what the party is after now, this session, in the campaign. Restate after a twist.
    [Lazy GM RD; Schell L#32; S&Z ch.24] V2 V4
57. **Give every scene a question; cut when it's answered.** Start just before the action; skip
    empty time in a sentence. [Alexandrian pacing; Fate scenes]
58. **Run tension in waves.** Build, hold briefly, let it finish, then a real rest (loot, banter,
    travel) before the next build. Never two climaxes back to back; never a lull without a new
    hook. [Booth (L4D director); MDA; S&Z ch.23]
59. **Alternate kinds of scene.** Fight, talk, exploration, puzzle; quiet scenes are the rests
    between peaks. [Laws p.16; Lazzaro]
60. **Show the bomb, and keep a question open.** Tell the players about the deadline or the
    assassin in the crowd and let the clock be felt; keep pure surprise for twists seeded in
    advance. Always leave a few open questions that matter to the PCs, with partial answers
    within reach. [Hitchcock; Loewenstein; Schell L#4, L#6] V4
61. **When play stalls, add a reason and a clock, not an order.** A threat that advances if they
    keep debating, a reward for committing; after three similar moves in a row, change something.
    [S&Z (Sneak notes); Ironsworn; Fate]

## 8. Steering without railroading

62. **Prep situations, not plots.** NPCs with wants, clocks, consequences, places; the story is
    what the table does with them. = CLAUDE.md *Plan as you go*. [Alexandrian; DW agenda; Schell L#73; S&Z ch.6]
63. **Never cancel a choice to force an outcome you had already decided.** Failure, consequences
    and NPCs pursuing their own goals are not railroading; overriding the players is. [Alexandrian railroading manifesto]
64. **Steer with the world, not with the players' hands.** A goal, a landmark on the horizon, an
    NPC they care about, a change of mood music; an NPC may serve your aim only while pursuing
    its own. [Schell ch.18, L#81-82]
65. **Say yes, or roll.** If nothing is at stake, it happens; sensible unplanned solutions work;
    getting from one situation to the next never hangs on one roll or one action. A route already
    crossed needs no new roll; party movement is one group check (CLAUDE.md Dice). [Baker; Laws p.20; D&D SRD 5.2 "Group Checks"]
66. **Let choices land now and echo later.** Narrate the immediate result clearly, then bring it
    back and point out the link ("the guard you spared opens the gate"). [S&Z ch.3; Meier]
67. **Hold your plans lightly; hand some decisions to honest devices.** Build on facts the
    players add. Outcomes you shouldn't pick on a whim (two factions clash, an NPC breaks) go to
    the NPC's wants, a clock, or an open roll, and you say so. [Blades; Fate; AW; Ironsworn oracle]

## 9. NPCs and the world

68. **Every named NPC gets a name, a want, a method, one playable trait and a voice.** Record them
    when they first matter (`gm-npc.sh create`, `set-inner`) so hover cards work. [Laws pp.22-24; DW; Blades; Schell L#87]
69. **NPCs remember and change.** Slights, kindnesses and debts go into `gm-npc.sh update`; on
    the party's return, show what changed because of them. [Schell L#91; S&Z ch.3]
70. **The world moves offscreen.** Threats advance (clocks, `gm-session.sh world-tick`) and the
    party hears through contacts and rumours; ignored dangers change things for good. [DW fronts; Blades factions]
71. **Established fiction is fixed.** Check scene context and `gm-recall.sh` before narrating;
    one contradiction costs trust in everything before it. [Blades; Schell ch.16]
72. **Keep geography persistent and readable.** Describe each place's ways out and record every
    one with `gm-location.sh connect "<here>" "<there>" "<path>"` so the players' map shows it;
    describe places that matter on arrival (`gm-location.sh describe`). Give each a landmark;
    mention a few distant places to make the world bigger. [Alexandrian; Colville; Schell ch.21, ch.23; DW "draw maps, leave blanks"] V5
73. **In a fight or chase, name the zones and keep distances consistent.** Two to four named
    zones, distances in feet, cover and height stated once and reused; restate positions when
    they change. The players' map shows places, not positions. [Fate zones; Laws p.29; S&Z ch.12; Schell L#26] V5 V4

## 10. Rewards and progress

74. **Persist, then say what changed hands, with numbers.** `gm-player.sh gold|inventory "<PC>"`
    first, then "98 gold: you now have 108". The table's private notice backs this up and never
    replaces it. = *Narration*. [S&Z ch.3 (discernable); Schell L#28; Caribbean Star notes] V6
75. **Make treasure buy what they want, and let them see what's out there.** Prices and better
    gear visible before they can afford them; items that matter in the climax. [Schell L#7, L#52; S&Z ch.17; Laws p.22] V6
76. **Mix the kinds of reward.** Renown, healing and supplies, access (keys, places, allies), new
    abilities, spectacle (`--loot` pictures), status; vary the timing. [S&Z ch.24; Schell L#46]
77. **Reward what you want the table to value.** Clever avoidance, negotiation and discovery earn
    `gm-player.sh award` like kills; XP announced in the story is awarded the same turn.
    = *Reward the spectacle*. [S&Z ch.30; CLAUDE.md] V6
78. **Split contested loot openly.** Some rewards per PC, some shared; if they can't agree, one
    divides and another picks first, rotating. Record who holds what. [S&Z ch.19 (cake division), ch.20] V3 V6
79. **Make progress visible.** Recaps of what they achieved, the map filling in, NPCs reacting to
    their name, clocks they stopped. [Schell L#55; Colville; S&Z ch.26] V5

## 11. Table social contract and safety

80. **Run a short session zero.** A one-sentence pitch, tone and lethality, what each player
    enjoys, the shared stake, safety. For a one-shot, two minutes at the table. [Lazy GM RD; Sly Flourish; Gnome Stew; AW]
81. **Say the table's conventions out loud, and again when someone joins.** Heroic or gritty;
    retreat is sometimes wise; rolls and DCs are public; whispers exist and what they're for; how
    to reach the GM privately; PvP, theft from the party and betrayal need both players' consent.
    [Laws p.27; S&Z ch.12, ch.28; Schell L#99] V3 V4
82. **Collect lines and veils, privately if a player prefers; the strictest answer binds.**
    Record them without names: `gm-note.sh rules "Table line: …"`. [Lazy GM RD; Lines & Veils (Edwards); Fate Condensed]
83. **Stop at once on a stop signal.** An "X" in an action or a private aside cuts or rewinds the
    content, no reason asked. Check in briefly before dark turns so pausing is normal. [X-Card (Stavropoulos); Lazy GM RD; Fate Condensed]
84. **Keep the game in the game.** Never seek the players' side chat; no real-world stakes;
    preference notes hold in-game behaviour only, under PC names; no personal data anywhere. [S&Z ch.33; Schell L#111; CLAUDE.md]

## 12. Feedback and review

85. **Treat each session as a playtest.** Two or three questions before ("did every PC get a
    clue route?"), the review after (`session-review.md`). [Schell L#103; S&Z ch.2]
86. **Ask briefly, never argue, and read for the problem behind a request.** Stars and wishes, or
    best moment / most frustrating / wanted to do but couldn't. "More combat" may mean "I want to
    feel effective". The host's verdict outranks your own read. [Lazy GM RD; Schell ch.28, L#107]
87. **State the problem in one line before changing anything.** Prefer a fix that solves two
    problems; and if the table is clearly having fun, don't fix it. [Schell L#14; S&Z ch.2 (Knizia); Laws p.33]

---

## Tensions and how we resolve them

**T1. Hidden or revealed DCs.** Some sources reveal every DC and AC (Lazy GM RD); others hide a
DC when it reflects what the character can't know (Alexandrian); hidden rolls leak less but feel
less fair (Gnome Stew). *Resolution:* the table shows every roll and its DC before the dice land,
and that stays. Hide only an **NPC's** roll whose result the PCs couldn't know (`--secret`, an
ambusher's Stealth) or a passive check. Never hide the difficulty of a task the character can
judge. Why: V3 (rolls are open, so consistency can be seen) and V4 (you can't choose without odds).

**T2. Fudging and mid-fight adjustment.** Lazy GM RD and the SRD's troubleshooting allow quiet
tweaks to monster hit points; Alexandrian, Schell and S&Z warn that hidden adjustment destroys
trust once noticed. *Resolution:* no hidden changes to numbers. Stat blocks are locked; a fight
is re-tuned only through visible fiction that applies to both sides (morale breaks, reinforcements,
the environment), and unrevealed plot may change freely. Why: V3, consistency.

**T3. Telling the cost before the roll.** Blades, Dungeon World and the Alexandrian's fail-forward
critique say to state the cost up front; gm-skills says to decide it before rolling and not tell
the player. *Resolution:* say the danger and the **kind** of cost before the roll (who hears, what
breaks, what it risks); the exact twist can stay unsaid. Why: V4 (the decision is theirs, made
knowing the cost); and a cost they couldn't foresee reads as punishment (V3). Flagged for gm-skills.

**T4. Bookkeeping during play.** Laws and the Angry GM want sheet work out of the spotlight; V6
wants every change told. *Resolution:* the change is told in one clause, with numbers, in the beat
it happens (that is the reward moment); persist first. Level-up choices, shopping lists and
splitting loot happen at rests or between sessions. Why: V6, and Laws agrees the gain itself is
the payoff.

**T5. Trickle or flood.** Laws wants exposition in small pieces as needed; GUMSHOE holds floating
clues back while the table is having fun. V2 says many clues, free, spread. *Resolution:* the
**routes** are many and the core clues free and public; what may be paced is optional detail and
NPCs' private secrets, never what the party needs to move or decide. Frustration releases
anything held. Why: V2 overrides pacing taste.

**T6. Private scenes and whispers.** Gnome Stew and Schell value planned private reveals; Laws
prefers open cutaways watched by everyone; S&Z wants the shared channel as default. *Resolution:*
public by default. `--to` only for what that character alone could know or would hide; never
information about one PC sent to another; when a whisper happens, a public line says something
private took place ("Mira reads the letter and pockets it"), and you plan when it surfaces. Note
that each player's Narrator tab and hover cards recall only what that player saw, so a whisper
splits the party's memory too. Why: V3 (what concerns a PC goes to that PC), V2 (clues to the table).

**T7. Spotlight: rotation or appetite.** Gnome Stew and S&Z rotate on a clock or every round;
Laws weights by preference and lets the casual player sit back. *Resolution:* the round structure
already gives every seated player an action each round; beyond that, balance is judged over the
session and arc and weighted by what each player wants, never by equal counts. Why: V3 in the
host's words: not total equalness, but balance.

**T8. "Yes, and" against consistency.** Improv, Fate and Dungeon World build on player
contributions; Blades and Schell hold the established fiction fixed. *Resolution:* say yes to
anything that doesn't contradict what is established or the agreed tone; a player-made fact
becomes established once accepted, and gets recorded. Why: V3 (a world that changes under you
isn't fair) and Golden Rule 4.

**T9. Fan of the characters, or lethal stakes.** "Be a fan" and power-fantasy advice (Laws p.9)
against CLAUDE.md's loseable game. *Resolution:* be a fan of their competence and their story,
not their safety: telegraph lethal danger, leave an exit, then let the dice fall. Why: V4 makes
danger fair, and fairness is what lets death be earned rather than inflicted.

---

*Attribution.* Paraphrased principles from open texts: Dungeon World (Sage LaTorra, Adam Koebel;
CC BY 3.0); Blades in the Dark (John Harper, One Seven Design; CC BY 3.0); Fate Core and Fate
Condensed (Evil Hat Productions; CC BY 3.0); Ironsworn (Shawn Tomkin; CC BY 4.0); System
Reference Document 5.2.1 (Wizards of the Coast; CC BY 4.0); Lazy GM's Resource Document (Michael
E. Shea; CC BY 4.0); GUMSHOE SRD (Pelgrane Press; CC BY 3.0). Other works are cited by chapter or
page and summarised, not quoted.
