#!/usr/bin/env python3
"""
Simple dice rolling library for D&D
Supports standard notation: 1d20, 3d6+2, 2d20kh1 (advantage), etc.
"""

import random
import re
from typing import List, Optional, Tuple, Dict

# The operating system's random source: unpredictable, never seeded, fair.
_rng = random.SystemRandom()

# Import colors for formatted output
try:
    from lib.colors import Colors, format_roll_result
except ImportError:
    # Fallback if running directly
    try:
        from colors import Colors, format_roll_result
    except ImportError:
        # No colors available - use plain text
        class Colors:
            RESET = ""
            RED = ""
            GREEN = ""
            YELLOW = ""
            CYAN = ""
            BOLD = ""
            BOLD_RED = ""
            BOLD_GREEN = ""
            BOLD_YELLOW = ""
            BOLD_CYAN = ""
            DIM = ""

        def format_roll_result(notation, rolls, total, is_crit=False, is_fumble=False):
            rolls_str = '+'.join(str(r) for r in rolls)
            base = f"🎲 {notation}: [{rolls_str}] = {total}"
            if is_crit:
                base += " ⚔️ CRITICAL HIT!"
            elif is_fumble:
                base += " 💀 CRITICAL MISS!"
            return base

class DiceRoller:
    def __init__(self):
        # Regex patterns for different dice notations
        self.simple_pattern = re.compile(r'(\d+)d(\d+)([+-]\d+)?')
        self.advantage_pattern = re.compile(r'(\d+)d(\d+)kh(\d+)([+-]\d+)?')  # keep highest
        self.disadvantage_pattern = re.compile(r'(\d+)d(\d+)kl(\d+)([+-]\d+)?')  # keep lowest
        
    def roll(self, notation: str) -> Dict:
        """
        Roll dice based on notation and return detailed results
        
        Returns dict with:
        - notation: original notation
        - rolls: individual die results
        - total: final total
        - natural_20: True if d20 rolled natural 20
        - natural_1: True if d20 rolled natural 1
        """
        notation = notation.strip()
        
        # Check for advantage (keep highest)
        match = self.advantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([_rng.randint(1, sides) for _ in range(count)], reverse=True)
            kept = rolls[:keep]
            return {
                'notation': notation,
                'rolls': rolls,
                'kept': kept,
                'discarded': rolls[keep:],
                'modifier': modifier,
                'total': sum(kept) + modifier,
                'type': 'advantage'
            }
        
        # Check for disadvantage (keep lowest)
        match = self.disadvantage_pattern.match(notation)
        if match:
            count, sides, keep = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(4)) if match.group(4) else 0
            rolls = sorted([_rng.randint(1, sides) for _ in range(count)])
            kept = rolls[:keep]
            return {
                'notation': notation,
                'rolls': rolls,
                'kept': kept,
                'discarded': rolls[keep:],
                'modifier': modifier,
                'total': sum(kept) + modifier,
                'type': 'disadvantage'
            }
        
        # Standard roll
        match = self.simple_pattern.match(notation)
        if match:
            count, sides = int(match.group(1)), int(match.group(2))
            if sides < 1:
                raise ValueError(f"Invalid die size: d{sides} (must be at least 1)")
            modifier = int(match.group(3)) if match.group(3) else 0

            rolls = [_rng.randint(1, sides) for _ in range(count)]
            total = sum(rolls) + modifier
            
            result = {
                'notation': notation,
                'rolls': rolls,
                'modifier': modifier,
                'total': total,
                'type': 'standard'
            }
            
            # Check for natural 20/1 on d20
            if sides == 20 and count == 1:
                if rolls[0] == 20:
                    result['natural_20'] = True
                elif rolls[0] == 1:
                    result['natural_1'] = True
                    
            return result
        
        raise ValueError(f"Invalid dice notation: {notation}")
    
    def format_result(self, result: Dict) -> str:
        """Format a roll result for display with colors"""
        if result['type'] == 'advantage':
            kept_str = '+'.join(str(r) for r in result['kept'])
            discarded_str = '+'.join(str(r) for r in result['discarded'])
            mod_str = f" {result.get('modifier', 0):+d}" if result.get('modifier', 0) != 0 else ""
            return f"🎲 {result['notation']}: {Colors.CYAN}[{kept_str}]{Colors.RESET} {Colors.DIM}(discarded: {discarded_str}){Colors.RESET}{mod_str} = {Colors.CYAN}{result['total']}{Colors.RESET}"

        elif result['type'] == 'disadvantage':
            kept_str = '+'.join(str(r) for r in result['kept'])
            discarded_str = '+'.join(str(r) for r in result['discarded'])
            mod_str = f" {result.get('modifier', 0):+d}" if result.get('modifier', 0) != 0 else ""
            return f"🎲 {result['notation']}: {Colors.CYAN}[{kept_str}]{Colors.RESET} {Colors.DIM}(discarded: {discarded_str}){Colors.RESET}{mod_str} = {Colors.CYAN}{result['total']}{Colors.RESET}"

        else:  # standard
            is_crit = result.get('natural_20', False)
            is_fumble = result.get('natural_1', False)

            rolls_str = '+'.join(str(r) for r in result['rolls'])
            base = f"🎲 {result['notation']}: {Colors.CYAN}[{rolls_str}]{Colors.RESET}"

            if result['modifier'] != 0:
                mod_str = f"{result['modifier']:+d}"
                base += f" {mod_str}"

            base += f" = {Colors.CYAN}{result['total']}{Colors.RESET}"

            if is_crit:
                base += f" ⚔️ {Colors.BOLD_GREEN}CRITICAL HIT!{Colors.RESET}"
            elif is_fumble:
                base += f" 💀 {Colors.BOLD_RED}CRITICAL MISS!{Colors.RESET}"

            return base


# Module-level convenience functions
_roller = DiceRoller()

def roll(notation: str) -> int:
    """Quick roll that returns just the total. Use for simple checks."""
    return _roller.roll(notation)['total']

def roll_detailed(notation: str) -> Dict:
    """Roll with full details (rolls, modifiers, crits, etc.)"""
    return _roller.roll(notation)

def roll_formatted(notation: str) -> str:
    """Roll and return formatted string for display."""
    result = _roller.roll(notation)
    return _roller.format_result(result)


def natural(result: Dict) -> Optional[int]:
    """20 or 1 when a single d20 decided the roll (advantage/disadvantage: the kept die)."""
    if not re.match(r"\d+d20(k[hl]1)?\b", result.get("notation", "").replace(" ", "")):
        return None
    dice = result.get("kept") if result.get("type") in ("advantage", "disadvantage") \
        else result.get("rolls")
    if not dice or len(dice) != 1:
        return None
    return dice[0] if dice[0] in (1, 20) else None


def judge(result: Dict, target: Optional[int]) -> Optional[str]:
    """'success' / 'failure' against a DC or AC set BEFORE the roll (meet or beat it).
    A natural 20 always succeeds and a natural 1 always fails."""
    if target is None:
        return None
    nat = natural(result)
    if nat == 20:
        return "success"
    if nat == 1:
        return "failure"
    return "success" if result["total"] >= target else "failure"


def describe(result: Dict, target: Optional[int], label: str = "DC") -> str:
    """The roll line plus its verdict, for the terminal."""
    line = DiceRoller().format_result(result)
    if result.get("type") in ("advantage", "disadvantage") and natural(result):
        line += " ⚔️ NATURAL 20!" if natural(result) == 20 else " 💀 NATURAL 1!"
    verdict = judge(result, target)
    if target is not None:
        line += f"  vs {label} {target} — " + ("✓ SUCCESS" if verdict == "success" else "✗ FAILURE")
    return line


def main():
    """CLI: roll dice. With an online table open, the TABLE rolls them and shows
    every roll to every player, with its DC/AC — fixed before the dice land."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Roll dice: 1d20+5, 3d6+2, 2d20kh1+3 (advantage), 2d20kl1 (disadvantage)")
    parser.add_argument("notation")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--dc", type=int, help="Difficulty class, set before rolling")
    target.add_argument("--ac", type=int, help="Armor class (attack rolls), set before rolling")
    parser.add_argument("--for", dest="pc", help="Who is rolling (a PC or NPC name)")
    parser.add_argument("--why", help="What the roll is for: 'Stealth', 'dagger damage'...")
    parser.add_argument("--why-he", help="The same, in Hebrew (shown to Hebrew players)")
    parser.add_argument("--why-en", help="The same, in English (shown to English players)")
    parser.add_argument("--secret", action="store_true",
                        help="A hidden roll: players see that the GM rolled, not the result")
    parser.add_argument("--local", action="store_true",
                        help="Roll here even if a table is open (not shown to players)")
    args = parser.parse_args()

    roller = DiceRoller()
    try:
        roller.roll(args.notation)          # validate before anything is announced
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    label = "AC" if args.ac is not None else "DC"
    goal = args.ac if args.ac is not None else args.dc

    if not args.local:
        try:
            from table_server import roll_at_table
        except ImportError:
            roll_at_table = None
        shown = roll_at_table({
            "notation": args.notation, "target": goal, "target_label": label,
            "pc": args.pc, "why": args.why,
            "why_tr": {k: v for k, v in (("he", args.why_he), ("en", args.why_en)) if v},
            "secret": args.secret}) if roll_at_table else None
        if shown is not None:
            if not shown.get("ok"):
                print(f"Error: {shown.get('error')}")
                sys.exit(1)
            print(describe(shown["result"], goal, label))
            print("   (rolled by the table — every player saw it"
                  + (", as a secret roll)" if args.secret else ")"))
            return

    print(describe(roller.roll(args.notation), goal, label))


def _utf8_console() -> None:
    """Print emoji and Hebrew on any console (Windows defaults to a legacy code page)."""
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    _utf8_console()
    main()