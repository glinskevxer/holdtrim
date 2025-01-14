"""Load control for a regional freighter operation.

The package is split by what a load controller actually does in a shift:
build up ULDs from consignments, plan them into hold positions, work the
weight and balance, screen the dangerous goods, and issue the loadsheet and
the teletype messages that follow it.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
