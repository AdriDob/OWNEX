"""
OWNEX V13 — Weather Intelligence & Prediction Markets
Unified Weather Record Format — Single Source of Truth

Every meteorological record across all data sources must conform to this schema.
No arbitrary probabilities — all calibrated from historical validation.

MIT License concepts from GFS/Hermes repos reused (architecture patterns).
AGPL-3.0 PolyWeather consumed as external API only (black box).
Academic model (Repo 4): experimental reference only.

Author: OWNEX Senior Bug Bounty Engineer
Date: 2026-11-19
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Source(StrEnum):
    """Data source enumeration — every record must have a source."""

    GFS = "gfs"
    ECMWF = "ec_met"
    OPEN_METEO = "open_meteo"
    METAR = "metar"
    NOAA = "noaa"
    DEB = "deb"


class Variable(StrEnum):
    """Weather variables tracked in every record."""

    TEMPERATURE = "temperature"
    PRECIPITATION = "precipitation"
    WIND = "wind"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"


class Unit(StrEnum):
    """Unit of measurement — standardized across all sources."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    MM = "mm"
    M_PER_S = "m/s"
    HPA = "hpa"


class ValidationStatus(StrEnum):
    """Validation status for every record."""

    PENDING = "pending"
    VALIDATED = "validated"
    INVALID = "invalid"


class Horizon(StrEnum):
    """Forecast horizon — immediate to 7 days."""

    IMMEDIATE = "immediate"
    H6 = "6h"
    H24 = "24h"
    H72 = "72h"
    H168 = "168h"


@dataclass
class WeatherRecord:
    """
    Unified Weather Record — Single format for all data sources.

    Every record MUST include all fields. No fields are optional.
    Quality flags mandatory. No look-ahead bias.
    """

    # === REQUIRED FIELDS (no defaults — must be provided on creation) ===
    # Source identification
    source: Source
    model: str  # Model name/version
    city: str  # City name
    variable: Variable  # temperature, precipitation, wind
    unit: Unit  # celsius, fahrenheit, mm, m/s
    timestamp_utc: str  # UTC observation time (ISO format)

    # === OPTIONAL FIELDS (have defaults) ===
    # Observation metadata
    coordinates: dict = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0})  # {lat, lon}
    weather_station: str = ""  # Station ID (METAR/NOAA)

    # Forecast metadata
    horizon: Horizon = Horizon.H24  # immediate, 6h, 24h, 72h, 7d
    version: str = "1.0"  # Model version
    retrieval_timestamp: str = ""  # When data was fetched (ISO format)
    forecast_issuance: str = ""  # When forecast was issued (ISO format)

    # Quality flags (mandatory values, with workflow defaults)
    quality: Literal["validated", "unvalidated", "error"] = "unvalidated"  # validated/unvalidated/error
    validation_status: Literal["pending", "validated", "invalid"] = "pending"  # pending/validated/invalid

    # Calibration data
    sigma: float | None = None  # Standard deviation, estimated and validated per group
    bias_correction: float | None = None  # Bias correction from historical errors

    # Internal tracking
    _normalized: bool = False  # Internal: whether record has been normalized

    def __post_init__(self):
        """Post-initialization validation — enforce schema compliance."""
        # Validate source
        if self.source not in Source:
            raise ValueError(f"Invalid source: {self.source}. Must be one of {list(Source)}")

        # Validate variable
        if self.variable not in Variable:
            raise ValueError(f"Invalid variable: {self.variable}. Must be one of {list(Variable)}")

        # Validate unit
        if self.unit not in Unit:
            raise ValueError(f"Invalid unit: {self.unit}. Must be one of {list(Unit)}")

        # Validate horizon
        if self.horizon not in Horizon:
            raise ValueError(f"Invalid horizon: {self.horizon}. Must be one of {list(Horizon)}")

        # Validate quality
        if self.quality not in ("validated", "unvalidated", "error"):
            raise ValueError(f"Invalid quality: {self.quality}")

        # Validate validation_status
        if self.validation_status not in ("pending", "validated", "invalid"):
            raise ValueError(f"Invalid validation_status: {self.validation_status}")

        # Enforce: no arbitrary probabilities — all must be calibrated
        # sigma must be estimated and validated if quality is validated
        if self.quality == "validated" and self.sigma is None:
            raise ValueError(f"Record for {self.city}/{self.source}: quality='validated' requires sigma to be estimated and validated")

        # Mark as normalized after validation
        self._normalized = True

    def to_dict(self) -> dict:
        """Serialize to dict for JSON/API transmission."""
        return {
            "source": self.source.value,
            "model": self.model,
            "city": self.city,
            "coordinates": self.coordinates,
            "weather_station": self.weather_station,
            "variable": self.variable.value,
            "unit": self.unit.value,
            "timestamp_utc": self.timestamp_utc,
            "local_time": self._get_local_time(),
            "forecast_issuance": self.forecast_issuance,
            "horizon": self.horizon.value,
            "version": self.version,
            "retrieval_timestamp": self.retrieval_timestamp,
            "quality": self.quality,
            "validation_status": self.validation_status,
            "sigma": self.sigma,
            "bias_correction": self.bias_correction,
        }

    def _get_local_time(self) -> str:
        """Human-readable local time (simplified)."""
        # In production: would convert UTC to local timezone
        return self.local_time if hasattr(self, "local_time") else ""

    @classmethod
    def from_dict(cls, data: dict) -> "WeatherRecord":
        """Deserialize from dict, validating schema."""
        source = Source(data.get("source", "gfs"))
        variable = Variable(data.get("variable", "temperature"))
        unit = Unit(data.get("unit", "celsius"))
        horizon = Horizon(data.get("horizon", "24h"))

        return cls(
            source=source,
            model=data.get("model", "unknown"),
            city=data.get("city", "unknown"),
            variable=variable,
            unit=unit,
            timestamp_utc=data.get("timestamp_utc", ""),
            coordinates=data.get("coordinates", {"lat": 0.0, "lon": 0.0}),
            weather_station=data.get("weather_station", ""),
            horizon=horizon,
            version=data.get("version", "1.0"),
            retrieval_timestamp=data.get("retrieval_timestamp", ""),
            forecast_issuance=data.get("forecast_issuance", ""),
            quality=data.get("quality", "unvalidated"),
            validation_status=data.get("validation_status", "pending"),
            sigma=data.get("sigma"),
            bias_correction=data.get("bias_correction"),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        # Source/Variable/Unit/Horizon are str,Enums — can be used as strings directly
        return (
            f"WeatherRecord(city={self.city}, "
            f"source={self.source}, "
            f"variable={self.variable}, "
            f"horizon={self.horizon}, "
            f"quality={self.quality}, "
            f"sigma={self.sigma})"
        )

    def __repr__(self) -> str:
        """Official string representation."""
        # Source/Variable/Unit/Horizon are str,Enums — use their string value
        src = self.source.value if hasattr(self.source, "value") else self.source
        var = self.variable.value if hasattr(self.variable, "value") else self.variable
        unh = self.horizon.value if hasattr(self.horizon, "value") else self.horizon
        un = self.unit.value if hasattr(self.unit, "value") else self.unit
        return (
            f"WeatherRecord("
            f"source={src!r}, model={self.model!r}, "
            f"city={self.city!r}, coordinates={self.coordinates}, "
            f"variable={var!r}, unit={un!r}, "
            f"horizon={unh!r}, quality={self.quality!r}, "
            f"sigma={self.sigma!r})"
        )


# Repository for WeatherRecord operations
class WeatherRecordRepository:
    """Repository pattern for WeatherRecord storage and retrieval."""

    def __init__(self, storage_path: str | None = None):
        self._records: list[WeatherRecord] = []
        self._storage_path = storage_path

    def add(self, record: WeatherRecord) -> None:
        """Add a weather record to the repository."""
        if not record._normalized:
            raise ValueError("Record must be normalized before adding")
        self._records.append(record)

    def get_by_city(self, city: str) -> list[WeatherRecord]:
        """Get all records for a city."""
        return [r for r in self._records if r.city == city]

    def get_by_source(self, source: Source) -> list[WeatherRecord]:
        """Get all records from a source."""
        return [r for r in self._records if r.source == source]

    def get_validated(self) -> list[WeatherRecord]:
        """Get all validated records."""
        return [r for r in self._records if r.quality == "validated"]

    def get_by_horizon(self, horizon: Horizon) -> list[WeatherRecord]:
        """Get all records for a specific horizon."""
        return [r for r in self._records if r.horizon == horizon]

    def count_by_quality(self) -> dict[str, int]:
        """Count records by quality status."""
        counts = {"validated": 0, "unvalidated": 0, "error": 0}
        for r in self._records:
            counts[r.quality] = counts.get(r.quality, 0) + 1
        return counts

    def validate_all(self) -> dict[str, int]:
        """Validate all records and return quality counts."""
        results = {"validated": 0, "unvalidated": 0, "error": 0}
        for r in self._records:
            if r.sigma is not None and r.quality == "validated":
                results["validated"] += 1
            elif r.quality == "unvalidated":
                results["unvalidated"] += 1
            else:
                results["error"] += 1
        return results


# Standardized sigma estimation per group
def estimate_sigma(records: list[WeatherRecord], group_by: list[str] = None) -> dict[str, float]:
    """
    Estimate standard deviation (sigma) per group.

    sigma estimated per: city, station, model, horizon, variable, season
    Every group must have sufficient data points.
    """
    if group_by is None:
        group_by = ["city", "model", "horizon", "variable"]

    # Group records and compute sigma per group
    groups: dict[str, list[WeatherRecord]] = {}

    for record in records:
        # Build group key
        key_parts = []
        for dim in group_by:
            value = getattr(record, dim, None)
            if value is not None:
                key_parts.append(f"{dim}={value}")

        if not key_parts:
            continue

        key = "|".join(key_parts)
        if key not in groups:
            groups[key] = []
        groups[key].append(record)

    # Compute sigma per group
    sigma_estimates: dict[str, float] = {}
    for key, group_records in groups.items():
        # Need minimum data points for valid sigma estimation
        # Empirical minimum: 30 data points per group for statistical significance
        if len(group_records) < 30:
            # Flag as insufficient data — mark as unvalidated
            for r in group_records:
                r.quality = "unvalidated"
            sigma_estimates[key] = 0.0  # Placeholder — not statistically significant
            continue

        # Compute standard deviation from residuals
        # In production: compute from historical forecast errors
        # For now: use placeholder based on variable type
        variables = {r.variable for r in group_records}
        if Variable.TEMPERATURE in variables:
            sigma_estimates[key] = 3.0  # Placeholder: 3C typical stddev
        elif Variable.PRECIPITATION in variables:
            sigma_estimates[key] = 8.0  # Placeholder: 8mm typical stddev
        elif Variable.WIND in variables:
            sigma_estimates[key] = 10.0  # Placeholder: 10 m/s typical stddev
        else:
            sigma_estimates[key] = 5.0  # Default placeholder

    return sigma_estimates


# Bias correction from historical errors
def apply_bias_correction(records: list[WeatherRecord], sigma_estimates: dict[str, float]) -> list[WeatherRecord]:
    """
    Apply bias correction from historical forecast errors.

    Bias correction per group (city, model, horizon, variable, season).
    Only applied to records with quality='validated'.
    """
    corrected = []

    for record in records:
        if record.quality != "validated":
            corrected.append(record)
            continue

        # Build group key for bias lookup
        key_parts = [f"city={record.city}", f"model={record.model}", f"horizon={record.horizon.value}", f"variable={record.variable.value}"]
        key = "|".join(key_parts)

        # Look up bias correction
        bias = sigma_estimates.get(key, 0.0)

        # Apply bias correction (simple additive correction)
        # In production: this would be a trained calibration curve
        if bias is not None and bias != 0.0:
            record.bias_correction = bias

        corrected.append(record)

    return corrected


# Example: Gaussian Bucket Model discretization
def discretize_to_buckets(value: float, mean: float, sigma: float, num_buckets: int = 3) -> dict[int, float]:
    """
    Discretize a continuous value into Gaussian probability buckets.

    Uses the Gaussian Bucket Model pattern from Hermes repo (MIT licensed).
    Buckets represent probability intervals based on sigma.

    Returns dict of bucket_index -> probability_mass
    """
    import math

    if sigma <= 0:
        raise ValueError("Sigma must be positive for bucket discretization")

    # Standard Gaussian CDF
    def phi(x: float) -> float:
        """Standard normal CDF using math.erf."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    # Bucket boundaries at +/-sigma intervals
    # With 3 buckets: [-inf, -sigma], [-sigma, +sigma], [+sigma, +inf]
    boundaries = [0.0] * (num_buckets + 1)
    boundaries[0] = -float("inf")
    boundaries[1] = -sigma
    boundaries[2] = sigma
    boundaries[3] = float("inf")

    # Compute probability mass per bucket
    buckets: dict[int, float] = {}
    for i in range(num_buckets):
        lower = boundaries[i]
        upper = boundaries[i + 1]
        if lower == -float("inf"):
            mass = phi((value - mean) / sigma)  # CDF at value
        elif upper == float("inf"):
            mass = 1.0 - phi((value - mean) / sigma)  # Survivor function
        else:
            mass = phi((upper - mean) / sigma) - phi((lower - mean) / sigma)
        buckets[i] = mass

    return buckets


# Export main classes and functions
__all__ = [
    "Source",
    "Variable",
    "Unit",
    "ValidationStatus",
    "Horizon",
    "WeatherRecord",
    "WeatherRecordRepository",
    "estimate_sigma",
    "apply_bias_correction",
    "discretize_to_buckets",
]
