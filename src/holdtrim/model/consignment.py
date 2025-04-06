"""A consignment: one air waybill's worth of cargo waiting to fly.

The weight that matters depends on who is asking. The ramp wants the gross
weight, because that is what the aeroplane has to lift. Revenue wants the
chargeable weight, which is the gross weight or the volumetric weight,
whichever is greater, because a shed full of pillows costs the same to fly as
a shed full of pillows.

Volumetric weight is a fixed ratio, not a measurement: a cubic metre of hold
counts as 167 kg. It is a commercial convention and it is written down in the
tariff, so it is a constant here and not a setting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from holdtrim.errors import DataError
from holdtrim.ids import AirWaybill, parse_station
from holdtrim.units import to_kilos, to_metres

VOLUMETRIC_KILOS_PER_CUBIC_METRE = 167


@dataclass(frozen=True)
class Consignment:
    """One air waybill, as the warehouse and the load controller see it."""

    awb: AirWaybill
    origin: str
    destination: str
    pieces: int
    gross_weight: int
    volume: Decimal
    commodity: str
    ready_on: date
    shipper: str = ""
    consignee: str = ""
    handling: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", parse_station(self.origin))
        object.__setattr__(self, "destination", parse_station(self.destination))
        if self.origin == self.destination:
            raise DataError(f"{self.awb} is going from {self.origin} to itself")
        if self.pieces <= 0:
            raise DataError(f"{self.awb} has no pieces")
        object.__setattr__(self, "gross_weight", to_kilos(self.gross_weight, what="gross weight"))
        if self.gross_weight <= 0:
            raise DataError(f"{self.awb} has no weight")
        object.__setattr__(self, "volume", to_metres(self.volume, what="volume"))
        if self.volume < 0:
            raise DataError(f"{self.awb} has a negative volume")
        commodity = self.commodity.strip()
        if not commodity:
            raise DataError(f"{self.awb} has no commodity description")
        object.__setattr__(self, "commodity", commodity)
        object.__setattr__(self, "shipper", self.shipper.strip())
        object.__setattr__(self, "consignee", self.consignee.strip())
        codes = tuple(sorted({code.strip().upper() for code in self.handling}))
        for code in codes:
            if len(code) != 3 or not code.isalnum():
                raise DataError(f"{self.awb} carries {code!r}, which is not a handling code")
        object.__setattr__(self, "handling", codes)

    @property
    def route(self) -> str:
        """Where it is going, the way a manifest writes it."""
        return f"{self.origin}{self.destination}"

    @property
    def volumetric_weight(self) -> int:
        """What the volume weighs under the tariff."""
        return to_kilos(self.volume * VOLUMETRIC_KILOS_PER_CUBIC_METRE)

    @property
    def chargeable_weight(self) -> int:
        """The greater of the gross weight and the volumetric weight."""
        return max(self.gross_weight, self.volumetric_weight)

    @property
    def bulky(self) -> bool:
        """True where the volume decides the charge rather than the scales."""
        return self.volumetric_weight > self.gross_weight

    @property
    def density(self) -> Decimal:
        """Kilograms per cubic metre, zero where no volume was measured."""
        if self.volume <= 0:
            return Decimal("0.0")
        return (Decimal(self.gross_weight) / self.volume).quantize(Decimal("0.1"))

    @property
    def average_piece(self) -> int:
        """What one piece weighs on average, rounded up."""
        return -(-self.gross_weight // self.pieces)

    def carries(self, code: str) -> bool:
        """Whether the waybill carries a handling code."""
        return code.strip().upper() in self.handling

    def describe(self) -> str:
        """One line for a manifest."""
        codes = " ".join(self.handling)
        line = f"{self.awb} {self.route} {self.pieces}/{self.gross_weight} {self.commodity}"
        return f"{line} {codes}".rstrip()
