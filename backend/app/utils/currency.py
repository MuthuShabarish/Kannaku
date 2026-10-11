from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP, InvalidOperation
from typing import Union


def to_decimal(val: Union[int, float, str, Decimal]) -> Decimal:
    """
    Safely convert numeric input to exact Decimal.
    Avoids float representation drift by converting float via string.
    """
    if isinstance(val, Decimal):
        return val
    if isinstance(val, float):
        return Decimal(str(val))
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Cannot convert value '{val}' to Decimal")


def round_banker(amount: Union[Decimal, float, str, int], places: int = 2) -> Decimal:
    """
    Banker's Rounding (Round Half to Even) to eliminate cumulative financial rounding bias.
    Standard accounting rule for invoice line items and tax calculations.
    """
    dec = to_decimal(amount)
    pattern = Decimal("10") ** -places
    return dec.quantize(pattern, rounding=ROUND_HALF_EVEN)


def round_cash_tender(amount: Union[Decimal, float, str, int], round_to_nearest_integer: bool = False) -> Decimal:
    """
    Format cash tender amounts.
    If round_to_nearest_integer is True (e.g. rapid cash counter mode in micro retail),
    rounds to nearest ₹1 integer. Otherwise maintains exact 2-decimal rounding.
    """
    dec = to_decimal(amount)
    if round_to_nearest_integer:
        return dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return round_banker(dec, places=2)


def format_currency(amount: Union[Decimal, float, str, int], symbol: str = "₹", places: int = 2) -> str:
    """
    Format monetary amount with thousand separators and currency symbol.
    Example: 1250000.5 -> '₹1,250,000.50' (or Indian number format)
    """
    rounded = round_banker(amount, places=places)
    # Format with 2 decimal places and standard commas
    formatted_num = f"{rounded:,.{places}f}"
    return f"{symbol}{formatted_num}"
