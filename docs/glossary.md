# holdtrim glossary

The words this package uses, in the sense the trade uses them.
Run `python -m holdtrim.tools.build_glossary` to write this file again.

**arm**

The distance from the datum to a position, in metres. Arms forward of the datum are negative.

**cpm**

Container pallet message. Exactly which device is in which position.

**cumulative limit**

A weight limit shared by a run of positions, always less than the sum of them. The limit that gets missed, because each position looks legal.

**demurrage**

What a station owes for holding a device past its free days.

**dry operating weight**

The aeroplane ready to work with no payload and no usable fuel: airframe, crew, their bags, and the equipment that lives on board.

**index**

A scaled moment. Weight times distance from the reference arm, divided by a constant the schedule chooses, added to a constant it also chooses.

**ldm**

Load distribution message. What is on board and roughly where.

**lemac**

The arm of the leading edge of the mean aerodynamic chord.

**lmc**

Last minute change. A change after the loadsheet is issued, written in a box and initialled, up to a weight the operator sets.

**loadsheet**

The document the commander signs. Every figure on it is derived and none is typed in.

**mac**

Mean aerodynamic chord. The centre of gravity is quoted as a percentage along it, and that percentage is what the crew set the trim from.

**notoc**

Notification to captain. What dangerous goods are on board and where, so that a fire in a hold is a known quantity.

**running load**

Weight per metre of fuselage under a position. A floor rating, checked separately from the position's weight limit.

**segregation**

Two classes of dangerous goods that may not share a position, and may not be in neighbouring positions when they are loose.

**tare**

What a device weighs empty. Dead weight the aeroplane lifts and nobody pays for.

**transport index**

How radioactive a package is, for loading purposes. The indices add up across the aeroplane and decide how far things have to be kept apart.

**ucm**

ULD control message. Which devices went on and came off.

**uld**

Unit load device. The container or pallet the cargo flies in. A certified one is part of the aeroplane and its tare weight is on the loadsheet.

**underload**

How much more payload the limits would have allowed. There are three limits and which one binds changes with the fuel.

**zero fuel weight**

Dry operating weight plus payload. The weight the wing carries as bending load, and the only one of the three a load controller can change.
