# holdtrim commands

Generated from the command line of holdtrim 0.1.0.
Run `python -m holdtrim.tools.build_docs` to write this file again.

### `holdtrim`

Load control for a regional freighter operation.

| option | what it does |
| --- | --- |
| `--book` | The SQLite book to work on. |

### `holdtrim about`

Say what this build is and what book it is pointed at.

## `holdtrim book`

Look after the book itself.

### `holdtrim book backup`

Copy the book somewhere safe.

Arguments: `destination`

### `holdtrim book counts`

How many rows are in each table worth counting.

### `holdtrim book verify`

Check the file over and report anything wrong with it.

## `holdtrim cargo`

The consignments waiting to fly.

### `holdtrim cargo accept`

Whether a waybill may go on a flight tonight.

Arguments: `awb`, `designator`, `day`

### `holdtrim cargo book`

Put a waybill on file.

Arguments: `awb`, `origin`, `destination`

| option | what it does |
| --- | --- |
| `--pieces` | How many pieces. |
| `--weight` | Gross weight in kilograms. |
| `--volume` | Volume in cubic metres. |
| `--commodity` | What it is. |
| `--ready` | The day it is ready to fly. |
| `--shc` | Special handling codes, space separated. |
| `--shipper` | Shipper name. |
| `--consignee` | Consignee name. |

### `holdtrim cargo build`

Build waybills into a device, in the order they are given.

    Nothing is written. This is the check the warehouse runs before it starts
    stacking, so that a device that will not take the load is found out about
    on paper rather than on a scale.

Arguments: `code`

| option | what it does |
| --- | --- |
| `--awb` | A waybill to load. |

### `holdtrim cargo list`

The waybills on file.

| option | what it does |
| --- | --- |
| `--from` | Only this origin. |
| `--to` | Only this destination. |
| `--ready-by` | Only what is ready by this day. |

### `holdtrim cargo remove`

Take a waybill off file.

Arguments: `awb`

### `holdtrim cargo show`

One waybill in full.

Arguments: `awb`

### `holdtrim cargo tonnage`

What is booked over one sector.

Arguments: `origin`, `destination`

## `holdtrim danger`

The dangerous goods and where they may go.

### `holdtrim danger classes`

The classes this build knows, and what they are called.

### `holdtrim danger clear`

Take every declared line off a waybill.

Arguments: `awb`

### `holdtrim danger declare`

Declare one line against a waybill.

Arguments: `awb`

| option | what it does |
| --- | --- |
| `--un` | The UN number. |
| `--name` | The proper shipping name. |
| `--hazard` | The class or division. |
| `--packages` | How many packages. |
| `--quantity` | Net quantity in one package. |
| `--unit` | The unit that quantity is in. |
| `--pg` | Packing group, blank where there is none. |
| `--pi` | Packing instruction. |
| `--risk` | A subsidiary risk. |
| `--cao` | Cargo aircraft only. |
| `--ti` | Transport index, for class 7. |

### `holdtrim danger limits`

How much of each class may be in one package.

### `holdtrim danger list`

Everything declared, or everything on one waybill.

| option | what it does |
| --- | --- |
| `--awb` | Only one waybill. |

### `holdtrim danger meaning`

What one class or division is called.

Arguments: `hazard`

### `holdtrim danger notoc`

Print the notification to captain.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--by` | Who prepared the notice. |
| `--place` | A waybill and a position, as AWB=POSITION. |

### `holdtrim danger screen`

Screen what is planned against the segregation rules.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--place` | A waybill and a position, as AWB=POSITION. |

## `holdtrim fleet`

The types this operation flies.

### `holdtrim fleet dump`

Write a registered type back out as a schedule document.

Arguments: `code`, `destination`

### `holdtrim fleet envelope`

The breakpoints of one certified envelope.

Arguments: `code`, `name`

### `holdtrim fleet load`

Register a type from its weight schedule document.

Arguments: `schedule`

### `holdtrim fleet positions`

The loading positions on a type, front to back.

Arguments: `code`

### `holdtrim fleet remove`

Take a type out of the register.

Arguments: `code`

### `holdtrim fleet show`

The certificate weights and the index geometry for one type.

Arguments: `code`

### `holdtrim fleet types`

Every registered type.

## `holdtrim flight`

The flights this office works.

### `holdtrim flight add`

Put a flight on file.

Arguments: `designator`, `day`, `registration`, `origin`, `destination`

| option | what it does |
| --- | --- |
| `--taxi` | Taxi fuel in kilograms. |
| `--trip` | Trip fuel in kilograms. |
| `--takeoff` | Takeoff fuel in kilograms. |
| `--crew` | Crew on board. |
| `--passenger` | A passenger flight, which refuses cargo only shipments. |

### `holdtrim flight fuel`

Record the fuel figures the flight plan came back with.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--taxi` | New taxi fuel. |
| `--trip` | New trip fuel. |
| `--takeoff` | New takeoff fuel. |

### `holdtrim flight list`

The flights on file.

| option | what it does |
| --- | --- |
| `--day` | Only one day. |
| `--tail` | Only one aeroplane. |
| `--open` | Only the flights still open. |

### `holdtrim flight remove`

Take a flight off file.

Arguments: `designator`, `day`

### `holdtrim flight show`

One flight in full, with the aeroplane it is on.

Arguments: `designator`, `day`

### `holdtrim flight status`

Move a flight on to its next state.

Arguments: `designator`, `day`, `status`

### `holdtrim init`

Create the book, or bring an existing one up to date.

## `holdtrim message`

The messages that leave when the aeroplane does.

### `holdtrim message cpm`

The container and pallet message.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--to` | Teletype address. |
| `--from` | Our own teletype address. |
| `--filed` | Filing time as DDHHMM. |
| `--by` | Who prepared the figures. |

### `holdtrim message ldm`

The load distribution message.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--to` | Teletype address. |
| `--from` | Our own teletype address. |
| `--filed` | Filing time as DDHHMM. |
| `--by` | Who prepared the figures. |

### `holdtrim message mvt`

The movement message, on departure or on arrival.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--off-blocks` | Time off blocks, as HHMM. |
| `--airborne` | Time airborne, as HHMM. |
| `--eta` | Estimated arrival, as HHMM. |
| `--touchdown` | Time on the runway, as HHMM. |
| `--on-blocks` | Time on stand, as HHMM. |
| `--delay` | A delay, as CODE/MINUTES. |
| `--to` | Teletype address. |
| `--from` | Our own teletype address. |
| `--filed` | Filing time as DDHHMM. |

### `holdtrim message plan`

The LDM and the CPM together, which is what actually gets sent.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--to` | Teletype address. |
| `--from` | Our own teletype address. |
| `--filed` | Filing time as DDHHMM. |

### `holdtrim message ucm`

The ULD control message.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--on` | A device going on, as CODE/STATE. |
| `--off` | A device coming off, as CODE/STATE. |
| `--to` | Teletype address. |
| `--from` | Our own teletype address. |
| `--filed` | Filing time as DDHHMM. |

## `holdtrim plan`

What goes where on a flight.

### `holdtrim plan auto`

Suggest a plan, heaviest first, aiming for the middle of the envelope.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--load` | A device and its gross, as CODE=KILOS. |

### `holdtrim plan check`

Run every limit check against the plan.

Arguments: `designator`, `day`

### `holdtrim plan clear`

Throw the plan away and start again.

Arguments: `designator`, `day`

### `holdtrim plan offload`

Say what has to come off, and what it should be.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--priority` | What a position was promised, as POSITION=LEVEL. |

### `holdtrim plan pull`

Take whatever is in a position back out.

Arguments: `designator`, `day`, `position`

### `holdtrim plan put`

Put something in a position.

Arguments: `designator`, `day`, `position`

| option | what it does |
| --- | --- |
| `--weight` | What is going in, in kilograms. |
| `--uld` | The device, left out for loose cargo. |
| `--to` | Where it comes off. |

### `holdtrim plan sequence`

The order to load in, checked step by step against the envelope.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--as-planned` | Use the order the plan is in. |
| `--unload` | Give the order things come off in. |

### `holdtrim plan show`

The plan as it stands.

Arguments: `designator`, `day`

## `holdtrim report`

The questions no single record answers.

### `holdtrim report day`

How full every flight on a day is.

Arguments: `day`

### `holdtrim report disagreements`

Where the register and the movement log do not agree.

Arguments: `station`

| option | what it does |
| --- | --- |
| `--on` | The day to compare the two records on. |

### `holdtrim report export`

Write the whole book out as CSV.

Arguments: `destination`

### `holdtrim report flight`

Everything the book holds about one flight.

Arguments: `designator`, `day`

### `holdtrim report import`

Read a booking file in, reporting the rows that would not go.

Arguments: `source`

### `holdtrim report standing`

What has been standing too long, and what it is costing.

Arguments: `station`

| option | what it does |
| --- | --- |
| `--on` | The day to read the stock as at. |
| `--free-days` | Days before charging. |
| `--rate` | Charge a day after that. |

### `holdtrim report stock`

What is standing at a station, by base size.

Arguments: `station`

## `holdtrim sheet`

The loadsheet and what goes on it.

### `holdtrim sheet findings`

Everything standing between this flight and a signed loadsheet.

Arguments: `designator`, `day`

### `holdtrim sheet history`

Every edition that has been issued for a flight.

Arguments: `designator`, `day`

### `holdtrim sheet issue`

Check the sheet, record it, close the flight, and hand it over.

    The edition is not asked for. It follows what has already been issued for
    this flight, because an edition number typed in by hand is an edition
    number that eventually repeats.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--by` | Who prepared it. |
| `--on` | The day it was issued, the flight day by default. |

### `holdtrim sheet print`

Print the loadsheet, whether or not it may be issued.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--by` | Who prepared it. |
| `--edition` | Which edition. |
| `--lmc` | A change, as POSITION=KILOS. |

### `holdtrim sheet summary`

The one line a handover note carries.

Arguments: `designator`, `day`

| option | what it does |
| --- | --- |
| `--by` | Who prepared it. |

## `holdtrim station`

The airports this operation works.

### `holdtrim station add`

Put a station in the register.

Arguments: `code`, `name`

| option | what it does |
| --- | --- |
| `--elevation` | Field elevation in feet. |
| `--agent` | Handling agent, blank where we handle ourselves. |
| `--free-days` | Free storage days. |

### `holdtrim station list`

Every station in the register.

### `holdtrim station remove`

Take a station out of the register.

Arguments: `code`

### `holdtrim station set`

Change what is already registered for a station.

Arguments: `code`

| option | what it does |
| --- | --- |
| `--name` | Change the name. |
| `--agent` | Change the handling agent. |
| `--free-days` | Change the free storage days. |

### `holdtrim station show`

One station in full.

Arguments: `code`

## `holdtrim tail`

The aeroplanes on the fleet.

### `holdtrim tail add`

Put an aeroplane on the fleet.

Arguments: `registration`, `type_code`

| option | what it does |
| --- | --- |
| `--dow` | Dry operating weight in kilograms. |
| `--doi` | Dry operating index off the schedule. |
| `--weighed` | The day of the weighing, YYYY-MM-DD. |
| `--serial` | Manufacturer serial number. |
| `--valid-months` | How long the weighing counts for. |

### `holdtrim tail list`

Every aeroplane on the fleet.

| option | what it does |
| --- | --- |
| `--type` | Only aeroplanes of one type. |

### `holdtrim tail remove`

Take an aeroplane off the fleet.

Arguments: `registration`

### `holdtrim tail show`

One aeroplane in full.

Arguments: `registration`

| option | what it does |
| --- | --- |
| `--on` | Read the weighing as at this day. |

### `holdtrim tail status`

Move an aeroplane in or out of service.

Arguments: `registration`, `status`

### `holdtrim tail vary`

Apply a variation to an aeroplane's dry operating figures.

Arguments: `registration`

| option | what it does |
| --- | --- |
| `--weight` | Change to the dry operating weight. |
| `--index` | Matching change to the dry operating index. |

### `holdtrim tail weighings`

Aeroplanes whose weighing has run out or is about to.

| option | what it does |
| --- | --- |
| `--on` | The day to read the fleet as at. |
| `--within` | Days to look ahead. |

## `holdtrim uld`

The devices, where they are and what state they are in.

### `holdtrim uld add`

Put a device on the register.

Arguments: `code`

| option | what it does |
| --- | --- |
| `--tare` | Tare weight in kilograms. |
| `--max-gross` | Maximum gross weight. |
| `--at` | Station it is standing at. |
| `--condition` | What state it is in. |
| `--contour` | Its contour. |

### `holdtrim uld condition`

Record a change of condition.

Arguments: `code`, `state`

### `holdtrim uld list`

The devices on the register.

| option | what it does |
| --- | --- |
| `--at` | Only the devices at one station. |
| `--base` | Only one base size. |
| `--serviceable` | Only the ones that may be loaded. |

### `holdtrim uld log`

One device's whole history.

Arguments: `code`

### `holdtrim uld move`

Record a device somewhere else, and log both halves of the move.

    A move is two facts, not one. It left somewhere and it arrived somewhere,
    and a log that only carries the arrival cannot tell you when the station it
    came from stopped being charged for it.

Arguments: `code`, `station`

| option | what it does |
| --- | --- |
| `--on` | The day it moved. |
| `--flight` | The flight it moved on, blank for a road move. |
| `--state` | What state it moved in. |

### `holdtrim uld record`

Put one movement in the log without touching the register.

Arguments: `code`, `station`, `direction`

| option | what it does |
| --- | --- |
| `--on` | The day it happened. |
| `--flight` | The flight it moved on, blank for a road move. |
| `--state` | What state it was in. |
| `--note` | Anything the next person needs to know. |

### `holdtrim uld remove`

Take a device off the register.

Arguments: `code`

### `holdtrim uld show`

One device in full.

Arguments: `code`

### `holdtrim uld stock`

How many of each base size stand at a station.

Arguments: `station`

### `holdtrim uld transit`

The devices that are somewhere between two stations.
