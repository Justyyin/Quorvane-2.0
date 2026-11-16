"""List the fixed reply texts of the commands that have no translation yet.

Usage: python scripts/missing_texts.py [language]

Texts that are built with f-strings are not listed because they contain names and numbers; they stay English.
"""

import ast
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("send_message", "send", "edit_message", "edit_original_response")


def wrapped_texts(root=ROOT):
    """Return {English text: number of uses} for every text passed to i18n.say in the command modules."""
    found = Counter()
    for path in sorted((root / "quorvane" / "cogs").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("say", "tr") and isinstance(node.func.value, ast.Name) and node.func.value.id == "i18n":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and len(arg.value) >= 5:
                        found[arg.value] += 1
                        break
    for path in sorted((root / "quorvane").rglob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STEPS" for t in node.targets) and isinstance(node.value, ast.Tuple):
                for pair in node.value.elts:
                    try:
                        values = ast.literal_eval(pair)
                    except ValueError:
                        continue
                    for value in values if isinstance(values, tuple) else ():
                        if isinstance(value, str):
                            found[value] += 1
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TEXTS" for t in node.targets) and isinstance(node.value, ast.Tuple):
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        found[item.value] += 1
                    elif isinstance(item, ast.Name):
                        value = constants(path).get(item.id)
                        if value:
                            found[value] += 1
    return found


def constants(path):
    """String constants assigned at the top of a module, for TEXTS entries that refer to a name."""
    out = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                try:
                    value = "".join(ast.literal_eval(part) for part in (node.value.values if isinstance(node.value, ast.JoinedStr) else [node.value]))
                except ValueError:
                    continue
            if isinstance(value, str):
                out[node.targets[0].id] = value
    return out


def missing(lang, root=ROOT):
    """Texts that the language file does not contain."""
    have = json.loads((root / "quorvane" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
    return {text: n for text, n in wrapped_texts(root).items() if text not in have}


def main():
    """Print the missing texts of one language, most used first."""
    lang = sys.argv[1] if len(sys.argv) > 1 else "de"
    items = missing(lang)
    for text, n in sorted(items.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{n:3d}  {text}")
    print(f"{len(items)} texts without translation in {lang}", file=sys.stderr)


if __name__ == "__main__":
    main()
