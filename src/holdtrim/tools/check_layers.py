"""Nothing imports upwards.

The package is a stack. Quantities and identifiers at the bottom, then the
records, then the arithmetic over them, then the documents, then the store,
then the command line. A module may import from its own layer or from any
layer below it, and never from one above.

This is not a style rule. An import that goes the wrong way is a piece of
knowledge in the wrong place, and the way it shows up later is that a change
to a report cannot be made without touching the definition of a kilogram. The
fuel and trim tables sat in the balance package for months and made the
aircraft type depend on the arithmetic that reads it, which is exactly the
thing this catches.
"""

from __future__ import annotations

import ast
import sys

from holdtrim.tools.sources import module_name, package_files, parsed, report, where

LAYERS: dict[str, int] = {
    "holdtrim": 0,
    "holdtrim.units": 0,
    "holdtrim.errors": 0,
    "holdtrim.ids": 0,
    "holdtrim.findings": 0,
    "holdtrim.model": 1,
    "holdtrim.balance": 2,
    "holdtrim.cargo": 2,
    "holdtrim.schedule": 2,
    "holdtrim.danger": 3,
    "holdtrim.plan": 3,
    "holdtrim.sheet": 4,
    "holdtrim.message": 5,
    "holdtrim.store": 6,
    "holdtrim.office": 7,
    "holdtrim.report": 8,
    "holdtrim.cli": 9,
    "holdtrim.tools": 10,
}


def layer_of(module: str) -> int:
    """Which layer a module sits in, taken from its package."""
    if module in LAYERS:
        return LAYERS[module]
    parts = module.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in LAYERS:
            return LAYERS[candidate]
        parts.pop()
    raise KeyError(module)


def imports(tree: ast.Module) -> list[str]:
    """Every holdtrim module a file imports."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if alias.name.startswith("holdtrim"))
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("holdtrim"):
            found.append(str(node.module))
    return found


def problems() -> list[str]:
    """Every import that goes up the stack instead of down it."""
    found: list[str] = []
    for path in package_files():
        name = module_name(path)
        try:
            here = layer_of(name)
        except KeyError:
            found.append(f"{where(path)}: {name} is in no layer this check knows about")
            continue
        for imported in imports(parsed(path)):
            try:
                there = layer_of(imported)
            except KeyError:
                found.append(f"{where(path)}: imports {imported}, which is in no layer")
                continue
            if there > here:
                found.append(
                    f"{where(path)}: {name} is at layer {here} and imports "
                    f"{imported} at layer {there}"
                )
    return found


def main() -> int:
    """Run the check and report."""
    return report(problems(), checked=len(package_files()), what="source files")


if __name__ == "__main__":
    sys.exit(main())
