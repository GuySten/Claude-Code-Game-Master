"""The music package (lib/music): the engine, with no game imports; the old names still work."""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
sys.path.insert(0, str(LIB))
GAME = {p.stem for p in LIB.glob("*.py")} - {p.stem for p in (LIB / "music").glob("*.py")}


def test_the_engine_imports_nothing_from_the_game_at_module_level():
    for f in (LIB / "music").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in tree.body:                                   # (module level: lazy hooks may stay in functions)
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            bad = set(names) & GAME
            assert not bad, f"{f.name} imports game module(s) {bad}"


def test_the_old_names_are_the_package_modules_themselves():
    import arrangement
    import orchestra
    from music import arrangement as a2, orchestra as o2
    assert arrangement is a2 and orchestra is o2                # (monkeypatching either patches both)


def test_the_old_script_paths_still_run():
    out = subprocess.run([sys.executable, str(LIB / "arrangement.py"), "--help"], capture_output=True, text=True)
    assert out.returncode == 0 and "check" in out.stdout


def test_a_piece_has_one_file_name_stem_everywhere():
    import score_music
    from music import slug
    assert score_music.slug is slug and slug("Ashen Saint") == "ashen-saint" and slug("קסטרל").startswith("piece-")


def test_a_rendered_score_keeps_its_real_title_in_its_file_name(tmp_path):
    import score_music
    assert score_music.real_title("Countess Isolde Varnay: the Last Waltz (her theme)") == "the-last-waltz"
    assert score_music.real_title("Kestrel's anthem") == ""                     # (no title: no suffix)
    out = score_music.target(tmp_path, {"as": "theme", "who": "Countess Isolde Varnay"},
                             title="Countess Isolde Varnay: the Last Waltz (her theme)")
    assert out.name == "countess-isolde-varnay-theme-score--the-last-waltz.ogg"
