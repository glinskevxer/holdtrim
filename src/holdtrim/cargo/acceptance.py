"""Whether a consignment may go on a particular flight.

Acceptance is asked twice and answered differently each time. At the counter
the question is whether the shipment is acceptable at all: is it declared, is
it packed, does anybody carry it. Here the question is narrower and later,
which is whether this shipment may go on this flight tonight.

That is nearly all a matter of matching: the sector has to be the one it is
booked over, it has to be ready by the day, and a shipment that may only fly on
a freighter may not go on a passenger aeroplane. The one interesting case is
weight: a single piece heavier than any position will take is not going
anywhere on this type, and finding that out at the aircraft is a wasted night.
"""

from __future__ import annotations

from holdtrim.cargo import handling
from holdtrim.findings import STOP, WATCH, Finding
from holdtrim.model.aircraft import AircraftType
from holdtrim.model.consignment import Consignment
from holdtrim.model.flight import Sector

ROUTE = "route"
READY = "ready"
CARGO_ONLY = "cargo only"
PIECE_WEIGHT = "piece weight"
CODES = "handling codes"
UNDERLOAD = "underload"


def route(consignment: Consignment, sector: Sector) -> tuple[Finding, ...]:
    """Whether the shipment is booked over the sector the flight is flying."""
    if consignment.origin != sector.origin:
        return (
            Finding(
                check=ROUTE,
                where=str(consignment.awb),
                detail=f"is booked out of {consignment.origin} and the flight leaves "
                f"{sector.origin}",
            ),
        )
    if consignment.destination != sector.destination:
        return (
            Finding(
                check=ROUTE,
                where=str(consignment.awb),
                detail=(
                    f"is booked to {consignment.destination} and the flight goes to "
                    f"{sector.destination}"
                ),
                severity=WATCH,
            ),
        )
    return ()


def ready(consignment: Consignment, sector: Sector) -> tuple[Finding, ...]:
    """Whether it will be in the shed in time."""
    if consignment.ready_on > sector.day:
        late = (consignment.ready_on - sector.day).days
        return (
            Finding(
                check=READY,
                where=str(consignment.awb),
                detail=f"is ready {late} day(s) after the flight leaves",
            ),
        )
    return ()


def carriage(consignment: Consignment, sector: Sector) -> tuple[Finding, ...]:
    """Whether this kind of aeroplane may carry it."""
    if handling.cargo_aircraft_only(consignment.handling) and not sector.freighter:
        return (
            Finding(
                check=CARGO_ONLY,
                where=str(consignment.awb),
                detail="may only fly on a freighter",
            ),
        )
    return ()


def pieces(consignment: Consignment, kind: AircraftType) -> tuple[Finding, ...]:
    """Whether the heaviest piece fits any position at all."""
    heaviest = max(position.max_weight for position in kind.layout.positions)
    if consignment.average_piece > heaviest:
        return (
            Finding(
                check=PIECE_WEIGHT,
                where=str(consignment.awb),
                detail=(
                    f"averages {consignment.average_piece} kg a piece and the biggest "
                    f"position on a {kind.code} takes {heaviest} kg"
                ),
                over_by=consignment.average_piece - heaviest,
            ),
        )
    return ()


def codes(consignment: Consignment) -> tuple[Finding, ...]:
    """Whether every handling code on it is one this build knows."""
    unknown = handling.unknown(consignment.handling)
    if unknown:
        return (
            Finding(
                check=CODES,
                where=str(consignment.awb),
                detail=f"carries {', '.join(unknown)}, which this build does not know",
                severity=WATCH,
            ),
        )
    return ()


def room(consignment: Consignment, underload: int) -> tuple[Finding, ...]:
    """Whether the flight has the weight left for it."""
    if consignment.gross_weight > underload:
        return (
            Finding(
                check=UNDERLOAD,
                where=str(consignment.awb),
                detail=f"weighs {consignment.gross_weight} kg and {underload} kg is left",
                over_by=consignment.gross_weight - underload,
            ),
        )
    return ()


def check(
    consignment: Consignment, sector: Sector, kind: AircraftType, *, underload: int | None = None
) -> tuple[Finding, ...]:
    """Every acceptance check, all of them run."""
    found = (
        *route(consignment, sector),
        *ready(consignment, sector),
        *carriage(consignment, sector),
        *pieces(consignment, kind),
        *codes(consignment),
    )
    if underload is not None:
        found = (*found, *room(consignment, underload))
    return found


def acceptable(findings: tuple[Finding, ...]) -> bool:
    """Whether nothing found stops it going."""
    return all(finding.severity != STOP for finding in findings)
