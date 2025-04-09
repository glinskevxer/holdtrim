"""Special handling codes, and what each one obliges the office to do.

These are the three letter codes that travel on the waybill and end up in the
SI line of a message. Most of them are a note to the ramp. A few of them are
rules: CAO says the shipment cannot go on an aeroplane carrying passengers,
NST says nothing may be stacked on it, and the R codes say there is dangerous
goods paperwork the captain has to be handed.

The list is deliberately short. It is the codes this operation actually sees,
not the whole of the IATA table, because a code nobody handles is a code
nobody has written a procedure for.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdtrim.errors import DataError


@dataclass(frozen=True)
class HandlingCode:
    """One code and the handling it obliges."""

    code: str
    meaning: str
    dangerous: bool = False
    cargo_aircraft_only: bool = False
    stackable: bool = True
    temperature_controlled: bool = False
    live: bool = False

    @property
    def needs_notoc(self) -> bool:
        """Dangerous goods and live animals both go on the captain's notice."""
        return self.dangerous or self.live


def _code(
    code: str,
    meaning: str,
    *,
    dangerous: bool = False,
    cargo_aircraft_only: bool = False,
    stackable: bool = True,
    temperature_controlled: bool = False,
    live: bool = False,
) -> tuple[str, HandlingCode]:
    return code, HandlingCode(
        code=code,
        meaning=meaning,
        dangerous=dangerous,
        cargo_aircraft_only=cargo_aircraft_only,
        stackable=stackable,
        temperature_controlled=temperature_controlled,
        live=live,
    )


CODES: dict[str, HandlingCode] = dict(
    (
        _code("AVI", "live animals", live=True, stackable=False),
        _code("PER", "perishable", temperature_controlled=True),
        _code("PES", "fish or seafood", temperature_controlled=True),
        _code("EAT", "foodstuffs"),
        _code("HEA", "heavy, over 150 kg a piece", stackable=False),
        _code("BIG", "outsized", stackable=False),
        _code("NST", "not stackable", stackable=False),
        _code("VAL", "valuable cargo"),
        _code("HUM", "human remains", stackable=False),
        _code("LHO", "living human organs", temperature_controlled=True, stackable=False),
        _code("DIP", "diplomatic mail"),
        _code("WET", "wet cargo", stackable=False),
        _code("MAG", "magnetised material"),
        _code("ICE", "dry ice", dangerous=True),
        _code("ELI", "lithium ion batteries", dangerous=True),
        _code("ELM", "lithium metal batteries", dangerous=True, cargo_aircraft_only=True),
        _code("RFL", "flammable liquid", dangerous=True),
        _code("RFS", "flammable solid", dangerous=True),
        _code("RCM", "corrosive", dangerous=True),
        _code("RMD", "miscellaneous dangerous goods", dangerous=True),
        _code("RNG", "non flammable gas", dangerous=True),
        _code("RFG", "flammable gas", dangerous=True, cargo_aircraft_only=True),
        _code("ROX", "oxidiser", dangerous=True),
        _code("RPB", "toxic substance", dangerous=True, cargo_aircraft_only=True),
        _code("RRW", "radioactive, category I white", dangerous=True),
        _code("RRY", "radioactive, category II or III yellow", dangerous=True),
        _code("RXB", "explosive, division 1.4B", dangerous=True, cargo_aircraft_only=True),
        _code("CAO", "cargo aircraft only", cargo_aircraft_only=True),
    )
)


def known(code: str) -> bool:
    """Whether this build handles that code."""
    return code.strip().upper() in CODES


def rule(code: str) -> HandlingCode:
    """The rule for one code."""
    wanted = code.strip().upper()
    if wanted not in CODES:
        raise DataError(f"{wanted} is not a handling code this build knows")
    return CODES[wanted]


def meaning(code: str) -> str:
    """What the code means in plain words."""
    return rule(code).meaning


def unknown(codes: tuple[str, ...]) -> tuple[str, ...]:
    """Whichever of these codes this build has never heard of."""
    return tuple(code.strip().upper() for code in codes if not known(code))


def dangerous(codes: tuple[str, ...]) -> tuple[str, ...]:
    """The codes among these that make the shipment dangerous goods."""
    return tuple(sorted(rule(code).code for code in codes if rule(code).dangerous))


def cargo_aircraft_only(codes: tuple[str, ...]) -> bool:
    """Whether anything here bars the shipment from a passenger flight."""
    return any(rule(code).cargo_aircraft_only for code in codes)


def stackable(codes: tuple[str, ...]) -> bool:
    """Whether anything may be put on top of this."""
    return all(rule(code).stackable for code in codes)


def needs_notoc(codes: tuple[str, ...]) -> bool:
    """Whether the captain has to be handed a notice for this."""
    return any(rule(code).needs_notoc for code in codes)


def temperature_controlled(codes: tuple[str, ...]) -> bool:
    """Whether this has to be kept in the cool room until loading."""
    return any(rule(code).temperature_controlled for code in codes)
