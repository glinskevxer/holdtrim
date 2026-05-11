# How holdtrim is put together

The package is a stack and imports only ever go downwards. `holdtrim.tools.check_layers`
enforces it, and the layer numbers live in that module rather than in this note,
because a number in a note is a number nobody runs.

## The layers, bottom to top

**Quantities and identifiers.** `holdtrim.units` for weights, arms and index,
`holdtrim.ids` for the waybill, ULD and flight identifiers, `holdtrim.errors`
for the codes the command line turns into exit statuses, and
`holdtrim.findings` for the one shape every check answers in.

**The records.** `holdtrim.model` holds frozen dataclasses that validate
themselves and know nothing about storage. The weight schedule lives here in
pieces: `holdtrim.model.aircraft`, `holdtrim.model.position`,
`holdtrim.model.hold`, `holdtrim.model.envelope`, `holdtrim.model.fuel` and
`holdtrim.model.trim`. The fuel and trim tables were in the balance package to
begin with, which made the type depend on the arithmetic that reads it.

**The arithmetic and the vocabulary.** `holdtrim.balance` turns a plan into the
three weights and reads them against the envelope. `holdtrim.cargo` handles
consignments, the special handling codes and building up a device.
`holdtrim.schedule` reads a weight schedule document in and writes one out.

**The rules over them.** `holdtrim.danger` for the segregation table, the
screening and the captain's notice. `holdtrim.plan` for assignments, the
allocator, the loading sequence, the offload and the last minute changes.

**The documents.** `holdtrim.sheet` is the loadsheet, as figures and as paper.
`holdtrim.message` is the teletype envelope and the messages that go in it.

**The book.** `holdtrim.store` is one SQLite file. Migrations are numbered and
never edited, `holdtrim.store.sqlite` is the only place a connection is opened,
and every aggregate has its own module.

**Above the book.** `holdtrim.office` assembles one flight's whole picture in
one place. `holdtrim.report` answers the questions no single record answers.
`holdtrim.cli` is the only interface. `holdtrim.tools` holds the checks CI runs.

## Decisions worth knowing about

**Nothing reads the wall clock.** Every date comes in as an argument.
`holdtrim.tools.check_clock` reads for the calls that would break it.

**Decimals are stored as text.** A balance arm is a decimal figure off a
published schedule, and a float would introduce error the schedule does not
have in the one place the arithmetic has to match the paper.

**Values are bound, never formatted.** `holdtrim.tools.check_sql` reads every
statement, and fixed fragments have to be named constants.

**A plan may be illegal.** `holdtrim.plan.loadplan` holds assignments and
refuses nothing but nonsense. Whether the plan may be flown is a separate
question with its own module, because a load controller builds an illegal plan
on the way to a legal one.

**Every check runs.** `holdtrim.balance.limits` does not stop at the first
refusal, because a controller fixing one problem wants the other three now.

**Policy lives in the book.** The last minute change tolerance and the
demurrage rates are settings. Certified weights are not, and there is no
command that can change one.
