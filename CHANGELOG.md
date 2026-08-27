# Changelog

Dates are the day the work landed on main.

## 1.0.0

The first release. A shift can be worked end to end and the walk in CI does it
on every push.

- Load planning: allocate, move, sequence, offload, and how much room is left
  in each position.
- Dangerous goods: declarations, segregation, quantity limits per package, and
  the captain's notice.
- The loadsheet is recorded when it is issued, so what was signed for is what
  comes back.
- Messages: LDM, CPM, UCM and MVT out, and a received LDM read back and
  compared against the book.
- Reports: the handover, a day's exceptions, capacity, station stock,
  demurrage, device flow, a whole flight file, and a period summary.
- The book looks after itself: doctor, sizes, query plans, tidy and prune.
- Policy figures are settings in the book. Certified weights are not.
- Twenty two checks run in CI, all of them ordinary modules with tests.

## 0.1.0

The first working version. A flight can be filed, planned, checked, and its
loadsheet issued, and the two messages that follow it can be sent.

- Weights, arms and index, with the rounding a published schedule uses.
- The waybill, ULD and flight identifiers, check digits included.
- The book: one SQLite file, eleven migrations, opened through one place.
- The weight schedule: structural limits, index geometry, hold layout,
  cumulative limits, three certified envelopes, the fuel index table and the
  trim table.
- The fleet: types, aeroplanes and their weighing expiry.
- Cargo: consignments, handling codes, ULDs and building them up.
- Dangerous goods: declarations, the segregation table, screening a planned
  load and the notification to captain.
- Balance: the three weights, the index chain, the envelope and the limits.
- Planning: assignments, an allocator, and last minute changes.
- The loadsheet, and the LDM, CPM and UCM.
- Reports: station stock, demurrage, capacity, and CSV in and out.
- Sixteen checks CI runs, all of them ordinary modules with tests.
