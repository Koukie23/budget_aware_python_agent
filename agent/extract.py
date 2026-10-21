"""Pull the intended function out of a model completion."""

from __future__ import annotations

import ast
import re

_DEF_LINE = re.compile(r"^(def\s+\w+\s*\(.*\))\s*:?\s*$")


def collapse_duplicate_defs(text: str) -> str:
    lines = text.replace("\r\n", "\n").splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        current = _DEF_LINE.match(lines[i])
        nxt = _DEF_LINE.match(lines[i + 1]) if i + 1 < len(lines) else None
        if current and nxt and current.group(1) == nxt.group(1):
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _pick_function(tree: ast.Module, function_name: str | None) -> ast.FunctionDef | None:
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return None
    if function_name:
        named = [f for f in funcs if f.name == function_name]
        if named:
            return named[0]
    return funcs[0]


def _emit(tree: ast.Module, func: ast.FunctionDef) -> str:
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    module = ast.Module(body=[*imports, func], type_ignores=[])
    ast.fix_missing_locations(module)
    return ast.unparse(module)


def extract_code(text: str, function_name: str | None = None) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    body = collapse_duplicate_defs((match.group(1) if match else text).replace("\r\n", "\n"))
    lines = body.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(("def ", "import ", "from ", "class "))),
        None,
    )
    if start is None:
        return body.strip()
    collected: list[str] = []
    last_ok = None
    for line in lines[start:]:
        collected.append(line)
        try:
            tree = ast.parse("\n".join(collected))
        except SyntaxError:
            continue
        func = _pick_function(tree, function_name)
        if func is None:
            continue
        last_ok = _emit(tree, func)
        extras = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
        if extras:
            break
    return last_ok or body.strip()
