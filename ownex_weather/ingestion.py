"""
OWNEX V13 — Weather Intelligence & Prediction Markets
Multi-Source Data Ingestion Engine

Aggregates data from: GFS (NOAA/NWS) + ECMWF + Open-Meteo + METAR + NOAA
PolyWeather: API external consumption only (black box, no code reuse)
All data normalized to unified WeatherRecord format

License: MIT concepts from GFS/Hermes repos. AGPL-3.0 PolyWeather API only.
No code copied from any repo. All new implementation.
"""

from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any

from .models import Horizon, Source, Unit, ValidationStatus, Variable, WeatherRecord, WeatherRecordRepository, apply_bias_correction, estimate_sigma

# --- Source Adapters ---


class IngestionStatus(StrEnum):
    """Status of the ingestion pipeline."""

    IDLE = "idle"
    FETCHING = "fetching"
    VALIDATING = "validating"
    COMPLETE = "complete"
    ERROR = "error"


class DataQuality(Enum):
    """Data quality flags."""

    VALIDATED = "validated"
    UNVALIDATED = "unvalidated"
    ERROR = "error"


# GFS Ensemble Ingestion (NOAA/NWS)
class GFSAdapter:
    """Adapter for NOAA/NWS GFS 31-member ensemble data."""

    NAME = "gfs"
    DEFAULT_HORIZONS = [Horizon.IMMEDIATE, Horizon.H6, Horizon.H24, Horizon.H72, Horizon.H168]
    MEMBERS = 31  # 31-member ensemble

    def __init__(self, api_base: str = "https://api.example.com/gfs", timeout: int = 30):
        self.api_base = api_base
        self.timeout = timeout
        self.status = IngestionStatus.IDLE

    def fetch(self, city: str, coordinates: dict, horizon: Horizon = Horizon.H24, variables: list[Variable] = None) -> WeatherRecord | None:
        """
        Fetch GFS ensemble data for a city.

        In production: real HTTP request to NOAA GFS API.
        Currently: returns structured record with quality='unvalidated'.
        """
        if variables is None:
            variables = [Variable.TEMPERATURE]

        self.status = IngestionStatus.FETCHING

        # Simulate API call - in production: real NOAA/NWS request
        # Would use: requests.get(gfs_endpoint, params={...}, timeout=self.timeout)
        try:
            # Placeholder: generate structured record
            now = datetime.now(UTC)
            record = WeatherRecord(
                source=Source.GFS,
                model=f"GFS-ENS-{self.MEMBERS}mbr",
                city=city,
                coordinates=coordinates,
                variable=variables[0] if variables else Variable.TEMPERATURE,
                unit=Unit.CELSIUS,
                timestamp_utc=now.isoformat(),
                local_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                forecast_issuance=now.isoformat(),
                horizon=horizon,
                version="2024.1",
                retrieval_timestamp=now.isoformat(),
                quality=DataQuality.UNVALIDATED.value,
                validation_status=ValidationStatus.PENDING.value,
                sigma=None,  # Will be estimated after validation
            )

            self.status = IngestionStatus.COMPLETE
            return record

        except Exception as e:
            self.status = IngestionStatus.ERROR
            print(f"GFS fetch error for {city}: {e}")
            return None

    def fetch_batch(self, queries: list[dict], max_concurrent: int = 5) -> list[WeatherRecord | None]:
        """Fetch batch of GFS records."""
        results = []
        for query in queries:
            record = self.fetch(
                city=query.get("city", ""),
                coordinates=query.get("coordinates", {"lat": 0.0, "lon": 0.0}),
                horizon=Horizon(query.get("horizon", "24h")),
                variables=query.get("variables", [Variable.TEMPERATURE]),
            )
            results.append(record)
        return results


# Open-Meteo API Ingestion
class OpenMeteoAdapter:
    """Adapter for Open-Meteo free weather API."""

    NAME = "open_meteo"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.status = IngestionStatus.IDLE

    def fetch(self, latitude: float, longitude: float, horizon: Horizon = Horizon.H24, variables: list[Variable] = None) -> WeatherRecord | None:
        """
        Fetch Open-Meteo data for coordinates.

        Open-Meteo API: no auth required, global coverage.
        """
        if variables is None:
            variables = [Variable.TEMPERATURE]

        self.status = IngestionStatus.FETCHING

        try:
            # Open-Meteo endpoint: https://api.open-meteo.com/v1/forecast
            # Parameters: latitude, longitude, hourly/daily variables, timezone
            # In production: real HTTP request
            now = datetime.now(UTC)

            record = WeatherRecord(
                source=Source.OPEN_METEO,
                model="open-meteo-v1",
                city=f"coords_{latitude:.4f}_{longitude:.4f}",
                coordinates={"lat": latitude, "lon": longitude},
                variable=variables[0] if variables else Variable.TEMPERATURE,
                unit=Unit.CELSIUS,
                timestamp_utc=now.isoformat(),
                local_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                forecast_issuance=now.isoformat(),
                horizon=horizon,
                version="v1.0",
                retrieval_timestamp=now.isoformat(),
                quality=DataQuality.UNVALIDATED.value,
                validation_status=ValidationStatus.PENDING.value,
                sigma=None,
            )

            self.status = IngestionStatus.COMPLETE
            return record

        except Exception as e:
            self.status = IngestionStatus.ERROR
            print(f"Open-Meteo fetch error: {e}")
            return None


# METAR Station Ingestion
class METARAdapter:
    """Adapter for METAR airport weather station data."""

    NAME = "metar"

    def __init__(self, station_cache: dict | None = None, timeout: int = 30):
        self.station_cache = station_cache or {}
        self.timeout = timeout
        self.status = IngestionStatus.IDLE

    def fetch(self, station_id: str, variables: list[Variable] = None) -> WeatherRecord | None:
        """
        Fetch METAR data for a station ID.

        METAR: airport weather reports, short-term (hours) to medium-term.
        """
        if variables is None:
            variables = [Variable.TEMPERATURE, Variable.PRESSURE, Variable.WIND]

        self.status = IngestionStatus.FETCHING

        try:
            # In production: fetch from NOAA METAR service or aviation APIs
            # Example: aviationweather.gov/adds/dataserver_current/raw
            # Format: KJFK 231853Z 25008KT 10SM FEW020 SCT150 22/10 A3012

            now = datetime.now(UTC)

            # Parse simulated METAR data
            record = WeatherRecord(
                source=Source.METAR,
                model=f"metar-{station_id}",
                city=station_id,  # Station serves as city identifier
                coordinates={"lat": 0.0, "lon": 0.0},  # Would lookup from DB
                weather_station=station_id,
                variable=variables[0] if variables else Variable.TEMPERATURE,
                unit=Unit.CELSIUS,
                timestamp_utc=now.isoformat(),
                local_time=now.strftime("%Y-%m-%d %H:%M:%S"),
                forecast_issuance=now.isoformat(),
                horizon=Horizon.IMMEDIATE,  # METAR is immediate/short-term
                version="current",
                retrieval_timestamp=now.isoformat(),
                quality=DataQuality.UNVALIDATED.value,
                validation_status=ValidationStatus.PENDING.value,
                sigma=None,
            )

            self.status = IngestionStatus.COMPLETE
            return record

        except Exception as e:
            self.status = IngestionStatus.ERROR
            print(f"METAR fetch error for {station_id}: {e}")
            return None


# NOAA Additional Data Ingestion
class NOAAAdapter:
    """Adapter for NOAA additional meteorological data."""

    NAME = "noaa"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.status = IngestionStatus.IDLE

    def fetch(self, city: str, coordinates: dict, variables: list[Variable] = None) -> WeatherRecord | None:
        """Fetch NOAA data for a city."""
        if variables is None:
            variables = [Variable.TEMPERATURE]

        self.status = IngestionStatus.FETCHING

        try:
            # NOAA API access via various endpoints
            # In production: real NOAA/NWS requests
            now = datetime.now(UTC)

            record = WeatherRecord(
                source=Source.NOAA,
                model="noaa-v1",
                city=city,
                coordinates=coordinates,
                variable=variables[0] if variables else Variable.TEMPERATURE,
                unit=Unit.CELSIUS,
                timestamp_utc=now.isoformat(),
                local_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                forecast_issuance=now.isoformat(),
                horizon=Horizon.H24,
                version="v1.0",
                retrieval_timestamp=now.isoformat(),
                quality=DataQuality.UNVALIDATED.value,
                validation_status=ValidationStatus.PENDING.value,
                sigma=None,
            )

            self.status = IngestionStatus.COMPLETE
            return record

        except Exception as e:
            self.status = IngestionStatus.ERROR
            print(f"NOAA fetch error for {city}: {e}")
            return None


# --- Prediction Markets Ingestion (Paper Trading Only) ---


class PolymarketAdapter:
    """
    PolyWeather API consumption — AGPL-3.0 external only.
    NO code reuse, NO implementation copying.
    Black box API service integration.
    """

    NAME = "polymarket"

    def __init__(self, api_base: str = "https://api.polyweather.example", timeout: int = 30, api_key: str | None = None):
        self.api_base = api_base
        self.timeout = timeout
        self.api_key = api_key
        self.status = IngestionStatus.IDLE
        # ⚠️ AGPL-3.0: consume as external API only
        # ❌ Cannot copy code/datasets from PolyWeather implementation

    def fetch(self, market_id: str, **kwargs) -> WeatherRecord | None:
        """
        Fetch from PolyWeather API — black box consumption.

        Pattern: HTTP request → response parsing → own data format.
        Never share implementation code or internal data structures.
        """
        self.status = IngestionStatus.FETCHING

        try:
            # AGPL-3.0 compliance: API external only
            # Real implementation would make HTTP request to PolyWeather service
            # Pattern: request → parse → normalize to WeatherRecord format
            # Never: copy PolyWeather internal logic or datasets

            now = datetime.now(UTC)

            record = WeatherRecord(
                source=Source.DEB,  # Using DEB as placeholder for external API
                model="polyweather-api",
                city=market_id,
                coordinates={"lat": 0.0, "lon": 0.0},
                variable=Variable.TEMPERATURE,
                unit=Unit.CELSIUS,
                timestamp_utc=now.isoformat(),
                local_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                forecast_issuance=now.isoformat(),
                horizon=Horizon.IMMEDIATE,
                version="api-v1",
                retrieval_timestamp=now.isoformat(),
                quality=DataQuality.UNVALIDATED.value,
                validation_status=ValidationStatus.PENDING.value,
                sigma=None,
            )

            self.status = IngestionStatus.COMPLETE
            return record

        except Exception as e:
            self.status = IngestionStatus.ERROR
            print(f"PolyWeather API error: {e}")
            # ⚠️ Per AGPL-3.0: log error, continue with own implementation
            return None


# --- Ingestion Pipeline Orchestrator ---


class IngestionPipeline:
    """Orchestrates multi-source data ingestion into unified WeatherRecord format."""

    def __init__(
        self,
        use_gfs: bool = True,
        use_ecmwf: bool = False,
        use_open_meteo: bool = True,
        use_metar: bool = False,
        use_noaa: bool = True,
        use_polymarket: bool = False,
    ):

        self.adapters: dict[str, Any] = {}
        self.repository: WeatherRecordRepository | None = None
        self.status = IngestionStatus.IDLE
        self.quality_counts: dict[str, int] = {"validated": 0, "unvalidated": 0, "error": 0}

        # Initialize adapters based on configuration
        if use_gfs:
            self.adapters["gfs"] = GFSAdapter()
        if use_open_meteo:
            self.adapters["open_meteo"] = OpenMeteoAdapter()
        if use_metar:
            self.adapters["metar"] = METARAdapter()
        if use_noaa:
            self.adapters["noaa"] = NOAAAdapter()
        if use_polymarket:
            self.adapters["polymarket"] = PolymarketAdapter()

        # ⚠️ PolyWeather: only as API external consumption, never code reuse
        # if use_polyweather:
        #     self.adapters["polyweather"] = PolymarketAdapter(...)

    def set_repository(self, repository: WeatherRecordRepository) -> None:
        """Set the record repository for storage."""
        self.repository = repository

    def ingest_all(self, queries: list[dict], source_filter: list[str] | None = None) -> dict[str, Any]:
        """
        Ingest data from all configured sources.

        Args:
            queries: List of query dicts with city/coordinates parameters
            source_filter: Optional list of source names to include

        Returns:
            Dict with ingestion statistics and records
        """
        self.status = IngestionStatus.FETCHING
        all_records: list[WeatherRecord] = []
        source_stats: dict[str, int] = {}

        # Determine which sources to use
        sources_to_use = source_filter or list(self.adapters.keys())

        for source_name in sources_to_use:
            if source_name not in self.adapters:
                print(f"Adapter not configured: {source_name}")
                continue

            self.adapters[source_name]
            source_stats[source_name] = 0

            # Fetch records for this source
            for query in queries:
                try:
                    # Get adapter for this source
                    adapter_name = source_name
                    adapter_obj = self.adapters.get(adapter_name)
                    if adapter_obj is None:
                        continue

                    # Fetch based on source type
                    if adapter_name == "gfs":
                        record = adapter_obj.fetch(
                            city=query.get("city", ""),
                            coordinates=query.get("coordinates", {"lat": 0.0, "lon": 0.0}),
                            horizon=Horizon(query.get("horizon", "24h")),
                        )
                    elif adapter_name == "open_meteo":
                        record = adapter_obj.fetch(
                            latitude=query.get("coordinates", {}).get("lat", 0.0),
                            longitude=query.get("coordinates", {}).get("lon", 0.0),
                            horizon=Horizon(query.get("horizon", "24h")),
                        )
                    elif adapter_name == "metar":
                        record = adapter_obj.fetch(
                            station_id=query.get("station_id", ""),
                        )
                    elif adapter_name == "noaa":
                        record = adapter_obj.fetch(
                            city=query.get("city", ""),
                            coordinates=query.get("coordinates", {"lat": 0.0, "lon": 0.0}),
                        )
                    elif adapter_name == "polymarket":
                        record = adapter_obj.fetch(
                            market_id=query.get("market_id", ""),
                        )
                    else:
                        continue

                    if record is not None:
                        # Validate and normalize
                        record.quality = DataQuality.UNVALIDATED.value
                        record.validation_status = ValidationStatus.PENDING.value

                        # Add to repository if available
                        if self.repository is not None:
                            self.repository.add(record)

                        all_records.append(record)
                        source_stats[source_name] = source_stats.get(source_name, 0) + 1

                except Exception as e:
                    print(f"Ingestion error for {source_name}: {e}")
                    source_stats[source_name] = source_stats.get(source_name, 0) + 0

        # Post-processing: estimate σ and apply bias correction
        # (Only after sufficient validated data is available)
        validated_records = [r for r in all_records if r.quality == "validated"]

        if len(validated_records) >= 30:  # Minimum for statistical significance
            sigma_groups = ["city", "model", "horizon", "variable"]
            sigma_estimates = estimate_sigma(validated_records, sigma_groups)
            apply_bias_correction(all_records, sigma_estimates)

            # Update quality counts
            self.quality_counts = self.repository.validate_all() if self.repository else {"validated": 0, "unvalidated": 0, "error": 0}
        else:
            # Insufficient data — mark as unvalidated
            for r in all_records:
                r.quality = "unvalidated"
            self.quality_counts = {"validated": 0, "unvalidated": len(all_records), "error": 0}

        self.status = IngestionStatus.COMPLETE

        return {
            "status": self.status.value,
            "total_records": len(all_records),
            "by_source": source_stats,
            "quality_counts": self.quality_counts,
            "records": [r.to_dict() for r in all_records],
        }

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status."""
        return {
            "pipeline_status": self.status.value,
            "adapters_configured": list(self.adapters.keys()),
            "quality_counts": self.quality_counts,
            "total_records": len(self.repository._records) if self.repository else 0,
        }
