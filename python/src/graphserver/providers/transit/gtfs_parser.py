"""GTFS parser for transit provider."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

import gtfs_kit as gk
import pandas as pd

from .types import Departure, Route, Stop, StopTime, Trip

# Progress display formatting constants
MILLION_THRESHOLD = 1_000_000
THOUSAND_THRESHOLD = 1_000

logger = logging.getLogger(__name__)


class GTFSParser:
    """Parser for GTFS data using gtfs-kit library."""

    def __init__(
        self,
        gtfs_path: str | Path,
        progress_callback: Callable[[str, int, int, float | None], None],
    ) -> None:
        """Initialize GTFS parser.

        Args:
            gtfs_path: Path to GTFS zip file or directory
            progress_callback: Callback function for progress updates
                (step_name, current_step, total_steps, sub_progress)
                sub_progress is 0.0-1.0 for progress within step, complete=None
        """
        self.gtfs_path = Path(gtfs_path)
        self.progress_callback = progress_callback

        # Step 1: Read GTFS feed
        self.progress_callback("Reading GTFS file...", 1, 9, None)
        self.feed = gk.read_feed(str(self.gtfs_path), dist_units="m")

        # Parse and store data
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, Route] = {}
        self.trips: dict[str, Trip] = {}
        self.stop_times: dict[str, list[StopTime]] = {}  # keyed by trip_id

        # Service calendar and indexing data structures
        self.service_calendar: dict[str, list[str]] = {}  # date_str -> [service_ids]
        # stop_id -> [(stop_time, trip)]
        self.stop_to_stop_times: dict[str, list[tuple[StopTime, Trip]]] = {}

        # Agency timezone for proper local time handling
        self.agency_timezone: str | None = None

        self._parse_data()

    def _parse_data(self) -> None:
        """Parse GTFS data into internal structures."""
        logger.info("Parsing GTFS data from %s", self.gtfs_path)

        # Step 2: Parse agency timezone
        self.progress_callback("Parsing agency timezone...", 2, 9, None)
        self._parse_agency_timezone()

        # Step 3: Parse stops
        self.progress_callback("Parsing stops...", 3, 9, None)
        self._parse_stops()

        # Step 4: Parse routes
        self.progress_callback("Parsing routes...", 4, 9, None)
        self._parse_routes()

        # Step 5: Parse trips
        self.progress_callback("Parsing trips...", 5, 9, None)
        self._parse_trips()

        # Step 6: Parse stop times (often the largest/slowest)
        self.progress_callback("Parsing stop times...", 6, 9, None)
        self._parse_stop_times()

        # Step 7: Sort stop times by sequence
        self.progress_callback("Sorting stop times...", 7, 9, None)
        for trip_id in self.stop_times:
            self.stop_times[trip_id].sort(key=lambda st: st.stop_sequence)

        # Step 8: Build service calendar and indices
        self.progress_callback("Building service calendar and indices...", 8, 9, None)
        self._build_service_calendar()
        self._build_stop_indices()

        logger.info(
            "Parsed GTFS data: %d stops, %d routes, %d trips",
            len(self.stops),
            len(self.routes),
            len(self.trips),
        )

    def _parse_stops(self) -> None:
        """Parse stops from GTFS data."""
        if self.feed.stops is not None:
            for _, stop_row in self.feed.stops.iterrows():
                parent_station = None
                if (
                    "parent_station" in stop_row
                    and str(stop_row["parent_station"]) != "nan"
                ):
                    parent_station = str(stop_row["parent_station"])

                stop_timezone = None
                if (
                    "stop_timezone" in stop_row
                    and str(stop_row["stop_timezone"]) != "nan"
                ):
                    stop_timezone = str(stop_row["stop_timezone"])

                # Handle NaN values in GTFS data
                location_type_value = stop_row.get("location_type", 0)
                try:
                    # Try to convert directly first
                    location_type_value = int(location_type_value)
                except (ValueError, TypeError):
                    # If conversion fails, use default value
                    location_type_value = 0

                stop = Stop(
                    stop_id=str(stop_row["stop_id"]),
                    stop_name=str(stop_row.get("stop_name", "")),
                    lat=float(stop_row["stop_lat"]),
                    lon=float(stop_row["stop_lon"]),
                    location_type=location_type_value,
                    parent_station=parent_station,
                    stop_timezone=stop_timezone,
                )
                self.stops[stop.stop_id] = stop

    def _parse_routes(self) -> None:
        """Parse routes from GTFS data."""
        if self.feed.routes is not None:
            for _, route_row in self.feed.routes.iterrows():
                agency_id = None
                if "agency_id" in route_row and str(route_row["agency_id"]) != "nan":
                    agency_id = str(route_row["agency_id"])

                route = Route(
                    route_id=str(route_row["route_id"]),
                    route_short_name=str(route_row.get("route_short_name", "")),
                    route_long_name=str(route_row.get("route_long_name", "")),
                    route_type=int(route_row["route_type"]),
                    agency_id=agency_id,
                )
                self.routes[route.route_id] = route

    def _parse_trips(self) -> None:
        """Parse trips from GTFS data."""
        if self.feed.trips is not None:
            for _, trip_row in self.feed.trips.iterrows():
                trip_headsign = None
                if (
                    "trip_headsign" in trip_row
                    and str(trip_row["trip_headsign"]) != "nan"
                ):
                    trip_headsign = str(trip_row["trip_headsign"])

                direction_id = None
                if "direction_id" in trip_row:
                    try:
                        direction_id = int(trip_row["direction_id"])
                    except (ValueError, TypeError):
                        direction_id = None

                shape_id = None
                if "shape_id" in trip_row and str(trip_row["shape_id"]) != "nan":
                    shape_id = str(trip_row["shape_id"])

                trip = Trip(
                    trip_id=str(trip_row["trip_id"]),
                    route_id=str(trip_row["route_id"]),
                    service_id=str(trip_row["service_id"]),
                    trip_headsign=trip_headsign,
                    direction_id=direction_id,
                    shape_id=shape_id,
                )
                self.trips[trip.trip_id] = trip

    def _parse_stop_times(self) -> None:
        """Parse stop times from GTFS data."""
        if self.feed.stop_times is None:
            return

        stop_times_df = self.feed.stop_times.copy()  # Avoid modifying original
        total_rows = len(stop_times_df)

        # Vectorized type conversions and defaults - much faster than row-by-row
        if "pickup_type" in stop_times_df.columns:
            stop_times_df["pickup_type"] = (
                pd.to_numeric(stop_times_df["pickup_type"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        else:
            stop_times_df["pickup_type"] = 0

        if "drop_off_type" in stop_times_df.columns:
            stop_times_df["drop_off_type"] = (
                pd.to_numeric(stop_times_df["drop_off_type"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        else:
            stop_times_df["drop_off_type"] = 0

        # Ensure string types for IDs (usually already strings)
        stop_times_df["trip_id"] = stop_times_df["trip_id"].astype(str)
        stop_times_df["stop_id"] = stop_times_df["stop_id"].astype(str)
        stop_times_df["arrival_time"] = stop_times_df["arrival_time"].astype(str)
        stop_times_df["departure_time"] = stop_times_df["departure_time"].astype(str)

        # Group by trip_id for efficient processing
        grouped = stop_times_df.groupby("trip_id", sort=False)
        processed_rows = 0
        update_interval = max(1, total_rows // 100)  # Update every 1% of records

        for trip_id, group_df in grouped:
            # Convert group to StopTime objects using list comprehension
            self.stop_times[trip_id] = [
                StopTime(
                    trip_id=trip_id,  # Reuse the group key
                    stop_id=row.stop_id,
                    stop_sequence=int(row.stop_sequence),
                    arrival_time=row.arrival_time,
                    departure_time=row.departure_time,
                    pickup_type=row.pickup_type,
                    drop_off_type=row.drop_off_type,
                )
                for row in group_df.itertuples(index=False)
            ]

            # Update progress periodically
            processed_rows += len(group_df)
            if processed_rows % update_interval == 0 or processed_rows == total_rows:
                sub_progress = processed_rows / total_rows
                # Format numbers with K/M suffixes for readability
                if total_rows >= MILLION_THRESHOLD:
                    progress_text = (
                        f"({processed_rows / MILLION_THRESHOLD:.1f}M/"
                        f"{total_rows / MILLION_THRESHOLD:.1f}M records)"
                    )
                elif total_rows >= THOUSAND_THRESHOLD:
                    progress_text = (
                        f"({processed_rows / THOUSAND_THRESHOLD:.1f}K/"
                        f"{total_rows / THOUSAND_THRESHOLD:.1f}K records)"
                    )
                else:
                    progress_text = f"({processed_rows}/{total_rows} records)"

                self.progress_callback(
                    f"Parsing stop times... {progress_text}", 5, 7, sub_progress
                )

    def _prepare_time_window(
        self, start_time: int, max_hours: int
    ) -> tuple[datetime, datetime, date, date]:
        """Prepare time window for departure search.

        Args:
            start_time: Start time as Unix timestamp
            max_hours: Maximum hours to look ahead

        Returns:
            Tuple of (start_datetime, end_datetime, start_date, end_date)
        """
        from datetime import timedelta

        # Convert start_time to date objects for service lookup using agency timezone
        start_datetime = self._localize_timestamp(start_time)
        end_time = start_time + (max_hours * 3600)
        end_datetime = self._localize_timestamp(end_time)

        # Get the date range we need to check for services
        # Include previous day to catch late-night services that run past midnight
        start_date = start_datetime.date() - timedelta(days=1)
        end_date = end_datetime.date()

        return start_datetime, end_datetime, start_date, end_date

    def _should_skip_stop_time(
        self, stop_time: StopTime, trip: Trip, active_services: set[str]
    ) -> bool:
        """Check if a stop time should be skipped during departure search.

        Args:
            stop_time: The stop time to check
            trip: The associated trip
            active_services: Set of active service IDs

        Returns:
            True if this stop time should be skipped
        """
        # Skip if this stop doesn't allow pickup
        if stop_time.pickup_type == 1:
            return True

        # Skip if trip's service is not active in our date range
        return trip.service_id not in active_services

    def _find_next_stop_info(
        self, stop_time: StopTime, service_date_timestamp: int
    ) -> tuple[str | None, int | None, int | None]:
        """Find information about the next stop in the trip.

        Args:
            stop_time: Current stop time
            service_date_timestamp: Service date timestamp for time calculations

        Returns:
            Tuple of (next_stop_id, next_stop_sequence, next_arrival_time)
        """
        next_stop_id = None
        next_stop_sequence = None
        next_arrival_time = None

        if stop_time.trip_id in self.stop_times:
            trip_stop_times = self.stop_times[stop_time.trip_id]

            # Find current stop in the trip's stop times
            current_index = None
            for i, st in enumerate(trip_stop_times):
                if st.stop_sequence == stop_time.stop_sequence:
                    current_index = i
                    break

            # Get next stop if exists
            if current_index is not None and current_index + 1 < len(trip_stop_times):
                next_stop_time = trip_stop_times[current_index + 1]
                next_stop_id = next_stop_time.stop_id
                next_stop_sequence = next_stop_time.stop_sequence
                next_arrival_time = self._normalize_departure_time(
                    next_stop_time.arrival_time, service_date_timestamp
                )

        return next_stop_id, next_stop_sequence, next_arrival_time

    def _process_service_date(
        self,
        stop_time: StopTime,
        trip: Trip,
        service_date_obj: date,
        start_time: int,
        end_time: int,
        stop_id: str,
    ) -> Departure | None:
        """Process a service date and create departure if valid.

        Args:
            stop_time: The stop time to process
            trip: The associated trip
            service_date_obj: Service date to check
            start_time: Start time as Unix timestamp
            end_time: End time as Unix timestamp
            stop_id: Stop ID for the departure

        Returns:
            Departure object if valid, None otherwise
        """
        service_date_timestamp = self._get_service_midnight(service_date_obj)

        # Check if service is active on this specific date
        services_for_date = self._get_services_for_date(service_date_obj)
        if trip.service_id not in services_for_date:
            return None

        # Calculate departure time for this service date
        departure_timestamp = self._normalize_departure_time(
            stop_time.departure_time, service_date_timestamp
        )
        arrival_timestamp = self._normalize_departure_time(
            stop_time.arrival_time, service_date_timestamp
        )

        # Check if departure is within our time window
        if departure_timestamp < start_time or departure_timestamp > end_time:
            return None

        # Find next stop in the trip
        next_stop_id, next_stop_sequence, next_arrival_time = self._find_next_stop_info(
            stop_time, service_date_timestamp
        )

        return Departure(
            trip_id=trip.trip_id,
            route_id=trip.route_id,
            stop_id=stop_id,
            stop_sequence=stop_time.stop_sequence,
            departure_time=departure_timestamp,
            arrival_time=arrival_timestamp,
            next_stop_id=next_stop_id,
            next_stop_sequence=next_stop_sequence,
            next_arrival_time=next_arrival_time,
        )

    def get_departures_from_stop(
        self,
        stop_id: str,
        start_time: int,
        max_hours: int = 24,
    ) -> Sequence[Departure]:
        """Get departures from a stop within time window.

        Args:
            stop_id: Stop ID
            start_time: Start time as Unix timestamp
            max_hours: Maximum hours to look ahead

        Returns:
            List of departures sorted by departure time
        """
        if stop_id not in self.stops:
            return []

        # Prepare time window for search
        start_datetime, _, start_date, end_date = self._prepare_time_window(
            start_time, max_hours
        )
        end_time = start_time + (max_hours * 3600)

        # Get all services active in this date range
        active_services = self._get_services_for_date_range(start_date, end_date)

        # Use the stop index to get only relevant stop times
        if stop_id not in self.stop_to_stop_times:
            return []

        departures = []

        # Process each stop time for this stop
        for stop_time, trip in self.stop_to_stop_times[stop_id]:
            # Skip stop times that don't allow pickup or aren't in active services
            if self._should_skip_stop_time(stop_time, trip, active_services):
                continue

            # Check both current day and previous day services
            for days_offset in [0, -1]:  # Current day, then previous day
                from datetime import timedelta

                service_date_obj = start_datetime.date() + timedelta(days=days_offset)

                departure = self._process_service_date(
                    stop_time, trip, service_date_obj, start_time, end_time, stop_id
                )

                if departure is not None:
                    departures.append(departure)

        # Sort by departure time and return
        departures.sort(key=lambda d: d.departure_time)
        return departures

    def _parse_agency_timezone(self) -> None:
        """Parse agency timezone from GTFS agency.txt."""
        if self.feed.agency is not None and not self.feed.agency.empty:
            # Get the first agency's timezone (GTFS spec requires all agencies
            # have same timezone)
            agency_row = self.feed.agency.iloc[0]

            agency_tz_val = agency_row.get("agency_timezone")
            if agency_tz_val is not None and str(agency_tz_val) != "nan":
                timezone_str = str(agency_tz_val).strip()
                if timezone_str:
                    # Validate timezone before storing
                    if self._validate_timezone(timezone_str):
                        self.agency_timezone = timezone_str
                        logger.info("Using agency timezone: %s", self.agency_timezone)
                    else:
                        logger.warning(
                            "Invalid agency timezone '%s', falling back to UTC",
                            timezone_str,
                        )
                        self.agency_timezone = "UTC"
                else:
                    logger.warning(
                        "Empty agency_timezone found in agency.txt, using UTC"
                    )
                    self.agency_timezone = "UTC"
            else:
                logger.warning("No agency_timezone found in agency.txt, using UTC")
                self.agency_timezone = "UTC"
        else:
            logger.warning("No agency.txt found in GTFS feed, using UTC")
            self.agency_timezone = "UTC"

    def _validate_timezone(self, timezone_str: str) -> bool:
        """Validate that a timezone string is recognized by the system.

        Args:
            timezone_str: Timezone identifier to validate

        Returns:
            True if timezone is valid, False otherwise
        """
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(timezone_str)
        except zoneinfo.ZoneInfoNotFoundError:
            return False
        else:
            return True

    def _get_agency_timezone(self) -> ZoneInfo:
        """Get the agency timezone as a timezone object."""
        import zoneinfo

        if self.agency_timezone:
            try:
                return zoneinfo.ZoneInfo(self.agency_timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                logger.warning(
                    "Invalid timezone '%s', falling back to UTC", self.agency_timezone
                )
                return zoneinfo.ZoneInfo("UTC")
        else:
            return zoneinfo.ZoneInfo("UTC")

    def _localize_timestamp(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to agency timezone-aware datetime."""
        from datetime import datetime

        try:
            agency_tz = self._get_agency_timezone()
            return datetime.fromtimestamp(timestamp, tz=agency_tz)
        except (OSError, ValueError) as e:
            logger.warning(
                "Failed to localize timestamp %s to timezone %s: %s",
                timestamp,
                self.agency_timezone,
                e,
            )
            # Fallback to UTC
            import zoneinfo

            return datetime.fromtimestamp(timestamp, tz=zoneinfo.ZoneInfo("UTC"))

    def _get_service_midnight(self, date_obj: date) -> int:
        """Get midnight timestamp for a date in agency timezone."""
        from datetime import datetime

        try:
            agency_tz = self._get_agency_timezone()
            midnight = datetime.combine(date_obj, datetime.min.time()).replace(
                tzinfo=agency_tz
            )
            return int(midnight.timestamp())
        except (OSError, ValueError) as e:
            logger.warning(
                "Failed to get service midnight for %s in timezone %s: %s",
                date_obj,
                self.agency_timezone,
                e,
            )
            # Fallback to UTC midnight
            import zoneinfo

            midnight = datetime.combine(date_obj, datetime.min.time()).replace(
                tzinfo=zoneinfo.ZoneInfo("UTC")
            )
            return int(midnight.timestamp())

    def _build_service_calendar(self) -> None:
        """Build service calendar mapping dates to active service IDs."""

        # Use gtfs-kit to get valid dates for this feed
        valid_dates = gk.calendar.get_dates(self.feed, as_date_obj=True)

        if not valid_dates:
            # If no calendar data, assume all services are always active
            logger.warning(
                "No calendar data found in GTFS feed, assuming all services are active"
            )
            return

        # For each valid date, determine which services are active
        for date_obj in valid_dates:
            date_str = date_obj.strftime("%Y%m%d")

            # Check each service to see if it's active on this date
            active_services = [
                service_id
                for service_id in self._get_all_service_ids()
                if self._is_service_active_on_date(service_id, date_obj)
            ]

            if active_services:
                self.service_calendar[date_str] = active_services

    def _get_all_service_ids(self) -> set[str]:
        """Get all service IDs from trips."""
        return {trip.service_id for trip in self.trips.values()}

    def _is_service_active_on_date(self, service_id: str, date_obj: date) -> bool:
        """Check if a service is active on a specific date using calendar logic."""
        # Check if service runs on this day of week from calendar
        if self.feed.calendar is not None:
            calendar_df = self.feed.calendar
            service_calendar = calendar_df[calendar_df["service_id"] == service_id]

            if not service_calendar.empty:
                service_row = service_calendar.iloc[0]

                # Check date range
                start_date = pd.to_datetime(
                    str(service_row["start_date"]), format="%Y%m%d"
                ).date()
                end_date = pd.to_datetime(
                    str(service_row["end_date"]), format="%Y%m%d"
                ).date()

                if date_obj < start_date or date_obj > end_date:
                    return False

                # Check day of week (Monday = 0)
                day_names = [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
                day_column = day_names[date_obj.weekday()]

                if day_column in service_row and service_row[day_column] != 1:
                    return False

        # Check calendar_dates for exceptions
        if self.feed.calendar_dates is not None:
            calendar_dates_df = self.feed.calendar_dates
            date_str = date_obj.strftime("%Y%m%d")

            exceptions = calendar_dates_df[
                (calendar_dates_df["service_id"] == service_id)
                & (calendar_dates_df["date"].astype(str) == date_str)
            ]

            if not exceptions.empty:
                exception_type = exceptions.iloc[0]["exception_type"]
                return bool(
                    exception_type == 1
                )  # 1 = service added, 2 = service removed

        return True  # Default to active if no specific rules found

    def _build_stop_indices(self) -> None:
        """Build stop-to-stop_time index for efficient departure lookups."""
        # Clear existing index
        self.stop_to_stop_times.clear()

        # Build index: stop_id -> [(stop_time, trip)]
        for trip_id, stop_times_list in self.stop_times.items():
            if trip_id not in self.trips:
                continue

            trip = self.trips[trip_id]

            for stop_time in stop_times_list:
                stop_id = stop_time.stop_id

                if stop_id not in self.stop_to_stop_times:
                    self.stop_to_stop_times[stop_id] = []

                self.stop_to_stop_times[stop_id].append((stop_time, trip))

    def _get_services_for_date(self, date_obj: date) -> list[str]:
        """Get all service IDs active on a specific date."""
        date_str = date_obj.strftime("%Y%m%d")
        return self.service_calendar.get(date_str, [])

    def _get_services_for_date_range(
        self, start_date: date, end_date: date
    ) -> set[str]:
        """Get all service IDs active within a date range."""

        active_services = set()
        current_date = start_date

        while current_date <= end_date:
            services = self._get_services_for_date(current_date)
            active_services.update(services)
            current_date += timedelta(days=1)

        return active_services

    def _normalize_departure_time(self, gtfs_time: str, service_date: int) -> int:
        """Convert GTFS time to Unix timestamp, handling times past midnight.

        Args:
            gtfs_time: GTFS time string (e.g., "08:30:00" or "25:30:00")
            service_date: Service date as Unix timestamp (midnight)

        Returns:
            Unix timestamp of the departure
        """
        from .types import parse_gtfs_time

        seconds_since_service_start = parse_gtfs_time(gtfs_time)
        return service_date + seconds_since_service_start

    def get_stop_time(self, trip_id: str, stop_sequence: int) -> StopTime | None:
        """Get the stop time for a specific trip and stop sequence.

        Args:
            trip_id: Trip ID
            stop_sequence: Stop sequence number

        Returns:
            StopTime object or None if not found
        """
        if trip_id not in self.stop_times:
            return None

        stop_times_list = self.stop_times[trip_id]

        # Find the stop time with matching sequence number
        for stop_time in stop_times_list:
            if stop_time.stop_sequence == stop_sequence:
                return stop_time

        return None

    def get_stop_id_from_sequence(self, trip_id: str, stop_sequence: int) -> str | None:
        """Get the stop ID for a specific trip and stop sequence.

        Args:
            trip_id: Trip ID
            stop_sequence: Stop sequence number

        Returns:
            Stop ID or None if not found
        """
        stop_time = self.get_stop_time(trip_id, stop_sequence)
        return stop_time.stop_id if stop_time is not None else None

    def get_next_stop_sequence(self, trip_id: str, stop_sequence: int) -> int | None:
        """Get the next stop sequence number in a trip.

        Args:
            trip_id: Trip ID
            stop_sequence: Current stop sequence

        Returns:
            Next stop sequence number or None if no next stop
        """
        if trip_id not in self.stop_times:
            return None

        stop_times_list = self.stop_times[trip_id]

        # Find the next stop with higher sequence number
        next_sequence = None
        for stop_time in stop_times_list:
            if stop_time.stop_sequence > stop_sequence and (
                next_sequence is None or stop_time.stop_sequence < next_sequence
            ):
                next_sequence = stop_time.stop_sequence

        return next_sequence

    def get_trip_stop_bounds(self, trip_id: str) -> tuple[int, int] | None:
        """Get the first and last stop sequences for a trip.

        Args:
            trip_id: Trip ID

        Returns:
            Tuple of (min_sequence, max_sequence) or None if trip not found
        """
        if trip_id not in self.stop_times:
            return None

        stop_times_list = self.stop_times[trip_id]
        if not stop_times_list:
            return None

        sequences = [st.stop_sequence for st in stop_times_list]
        return (min(sequences), max(sequences))

    def is_service_active(self, service_id: str, date_obj: date) -> bool:
        """Check if a service is active on a given date.

        Args:
            service_id: Service ID
            date_obj: Date to check

        Returns:
            True if service is active
        """
        return self._is_service_active_on_date(service_id, date_obj)

    @property
    def stop_count(self) -> int:
        """Get number of stops."""
        return len(self.stops)

    @property
    def route_count(self) -> int:
        """Get number of routes."""
        return len(self.routes)

    @property
    def trip_count(self) -> int:
        """Get number of trips."""
        return len(self.trips)
