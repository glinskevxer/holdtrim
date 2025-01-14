# holdtrim

Load control for a regional freighter operation.

This is the office side of turning a night's cargo into a legal aeroplane: the
consignments that arrive at the warehouse, the ULDs they are built into, the
hold positions those ULDs go in, the weight and balance that comes out of it,
and the loadsheet and messages that leave when the aircraft does.

It is a command line tool over a single SQLite book. There is no server and no
network call anywhere in it, on purpose. A load controller works a shift with
the book in front of them, and the book has to be readable a year later when
somebody asks why a flight went out at that trim.

## Where things are

    src/holdtrim/units.py    weights, arms and index, and the rounding they use
    src/holdtrim/errors.py   the error codes the CLI and the reports quote
    tests/                   one directory per area, mirroring the package

## Running the checks

    python -m pip install -e ".[dev]" -c constraints.txt
    python -m pytest -q
    python -m ruff check .
    python -m mypy

## Units

Weight is whole kilograms everywhere. Arms are metres to three places. Index is
signed and carries one place. Rounding is half up, away from zero, which is
what a published weight schedule means when it prints 12.5.
