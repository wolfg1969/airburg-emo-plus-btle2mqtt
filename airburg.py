from dataclasses import dataclass

@dataclass(frozen=True)
class AirburgReading:
    """Parsed PM2.5 density and particle count reading."""

    density: int
    count: int
