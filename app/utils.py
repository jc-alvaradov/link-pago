def format_clp(amount: int) -> str:
    """Format amount as Chilean Peso currency string."""
    return f"${amount:,.0f}".replace(",", ".")
