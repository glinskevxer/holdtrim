# holdtrim

Load control for a regional freighter operation.

This is the office side of turning a night's cargo into a legal aeroplane. The
consignments that arrive at the warehouse, the ULDs they are built into, the
hold positions those ULDs go in, the weight and balance that comes out of it,
the dangerous goods screening, and the loadsheet and messages that leave when
the aircraft does.

It is a command line tool over a single SQLite book. There is no server and no
network call anywhere in it, on purpose. A load controller works a shift with
the book in front of them, and the book has to be readable a year later when
somebody asks why a flight went out at that trim.

## A shift, end to end

    holdtrim --book night.sqlite3 init
    holdtrim --book night.sqlite3 station add BLL Billund --elevation 247
    holdtrim --book night.sqlite3 fleet load examples/at7f.json
    holdtrim --book night.sqlite3 tail add OY-JAF AT7F --dow 13640 --doi 46.2 \
        --weighed 2024-06-18
    holdtrim --book night.sqlite3 uld add PMC12345QH --tare 110 --max-gross 4626 --at BLL
    holdtrim --book night.sqlite3 cargo book 125-12345675 BLL LGG --pieces 8 \
        --weight 1240 --volume 4.2 --commodity "machine parts" --ready 2025-05-11
    holdtrim --book night.sqlite3 flight add QH412 2025-05-12 OY-JAF BLL LGG \
        --taxi 90 --trip 1450 --takeoff 2600
    holdtrim --book night.sqlite3 plan auto QH412 2025-05-12 --load PMC12345QH=2000
    holdtrim --book night.sqlite3 plan check QH412 2025-05-12
    holdtrim --book night.sqlite3 sheet print QH412 2025-05-12 --by "K Ravn"
    holdtrim --book night.sqlite3 sheet issue QH412 2025-05-12 --by "K Ravn"
    holdtrim --book night.sqlite3 message plan QH412 2025-05-12 \
        --to LGGKLQH --from BLLLDQH --filed 121815

Every command is in `docs/commands.md`, which is generated from the commands
themselves. The words the trade uses are in `docs/glossary.md`, and the shape
of the book is in `docs/schema.sql`.

## Where things are

    src/holdtrim/units.py      weights, arms and index, and the rounding they use
    src/holdtrim/errors.py     the error codes the CLI and the reports quote
    src/holdtrim/ids.py        waybill, ULD and flight identifiers
    src/holdtrim/model/        the records, frozen, with no idea a database exists
    src/holdtrim/balance/      index arithmetic, the envelope, the limits
    src/holdtrim/cargo/        consignments, handling codes, building up
    src/holdtrim/danger/       the segregation table, screening, the captain's notice
    src/holdtrim/plan/         assignments, allocation, sequence, offload, LMC
    src/holdtrim/sheet/        the loadsheet, as figures and as paper
    src/holdtrim/message/      LDM, CPM, UCM and the teletype envelope
    src/holdtrim/store/        the book: migrations, one file per aggregate
    src/holdtrim/report/       the questions no single record answers
    src/holdtrim/cli/          the command line
    src/holdtrim/tools/        the checks CI runs, tested like anything else
    tests/                     one directory per area, mirroring the package

## Running the checks

    python -m pip install -e ".[dev]" -c constraints.txt
    python -m pytest -q
    python -m ruff check .
    python -m ruff format --check .
    python -m mypy
    python -m holdtrim.tools.check_layers

The whole list of checks is the lint job in `.github/workflows/ci.yml`. They
are ordinary modules under `src/holdtrim/tools/`, so any of them can be run on
its own before pushing.

## Units

Weight is whole kilograms everywhere. Arms are metres to three places. Index is
signed and carries one place. Rounding is half up, away from zero, which is
what a published weight schedule means when it prints 12.5.

Nothing in the package reads the wall clock. Every date comes in as an
argument, because the office is usually working a flight that leaves tomorrow.
