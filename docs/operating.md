# Working a shift with holdtrim

This is the order things happen in on a normal night, and where to look when
they do not. Every command here is in `docs/commands.md` with its options.

## Before anything

The `book` group looks after the file itself: `book doctor` reads it over,
`book verify` checks it, `book sizes` and `book plans` say how big it is
getting and how sqlite is answering the reports, `book backup` copies it and
`book prune` takes old seasons out.

    holdtrim book doctor
    holdtrim report handover BLL --on 2025-05-12

The doctor reads the book over for what the foreign keys cannot catch. The
handover is what the last shift left behind: flights still open, flights closed
with no loadsheet, weighings running out, devices that started costing money.

## Setting the office up

The `station` group holds the airports, the `fleet` group holds the types and
their weight schedules, and the `tail` group holds the aeroplanes. A schedule
is loaded from a document with `fleet load` and compared against a reissue with
`fleet compare`. The `setting` group holds the figures that are policy: the
last minute change tolerance and the demurrage rates.

## Taking the cargo

The `cargo` group is the waybill file. Bookings arrive overnight and go in with
`report import`, or one at a time with `cargo book`. `cargo accept` answers
whether a waybill may go on a particular flight, and `cargo build` checks a
device build up on paper before the warehouse starts stacking. Weights get
corrected against the scales with `cargo reweigh`.

The `uld` group is the device register and the movement log. `uld move` records
both halves of a move, `uld log` is one device's history.

Anything dangerous goes in the `danger` group. Declare the lines against the
waybill, then `danger screen` the planned load and print the `danger notoc`.

## Planning the flight

The `flight` group files the sector and its fuel. The `plan` group builds the
load: `plan auto` suggests one, `plan put` and `plan pull` change it by hand,
`plan check` runs every limit, `plan sequence` gives the order to load in and
`plan offload` says what comes off when it will not all go.

## Sending it

The `sheet` group prints and issues the loadsheet. Issuing records the edition,
so `sheet history` is what was signed for rather than what the book says now.
The `message` group sends the LDM, the CPM, the UCM and the MVT, and reads a
received message back with `message compare`.

`flight depart` records the aeroplane as gone, and refuses while anything is
still standing in the way.

## Afterwards

The `report` group is everything else: `report day` and `report period` for how
full the flights were, `report stock`, `report standing` and `report flow` for
the devices, `report flight` for one flight's whole file, and `report export`
for a spreadsheet.

## When something is wrong

    holdtrim sheet findings QH412 2025-05-12
    holdtrim report exceptions --on 2025-05-12
    holdtrim book doctor

Exit statuses are worth branching on: 2 is bad input, 3 is not found, 4 is a
duplicate, 5 is the wrong state, 6 is a rule saying no, and 7 is the book
itself.
