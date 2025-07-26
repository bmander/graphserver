"""GTFS parser for transit provider."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import gtfs_kit as gk

from .types import Departure, Route, Stop, StopTime, Trip, gtfs_time_to_timestamp

logger = logging.getLogger(__name__)


class GTFSParser:
    """Parser for GTFS data using gtfs-kit library."""

    def __init__(self, gtfs_path: str | Path) -> None:
        """Initialize GTFS parser.

        Args:
            gtfs_path: Path to GTFS zip file or directory
        """
        self.gtfs_path = Path(gtfs_path)
        self.feed = gk.read_feed(str(self.gtfs_path), dist_units="m")

        # Parse and store data
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, Route] = {}
        self.trips: dict[str, Trip] = {}
        self.stop_times: dict[str, list[StopTime]] = {}  # keyed by trip_id

        self._parse_data()

    def _parse_data(self) -> None:
        """Parse GTFS data into internal structures."""
        logger.info("Parsing GTFS data from %s", self.gtfs_path)

        self._parse_stops()
        self._parse_routes()
        self._parse_trips()
        self._parse_stop_times()

        # Sort stop times by sequence
        for trip_id in self.stop_times:
            self.stop_times[trip_id].sort(key=lambda st: st.stop_sequence)

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
                if ("parent_station" in stop_row
                    and str(stop_row["parent_station"]) != "nan"):
                    parent_station = str(stop_row["parent_station"])

                stop_timezone = None
                if ("stop_timezone" in stop_row
                    and str(stop_row["stop_timezone"]) != "nan"):
                    stop_timezone = str(stop_row["stop_timezone"])

                stop = Stop(
                    stop_id=str(stop_row["stop_id"]),
                    stop_name=str(stop_row.get("stop_name", "")),
                    lat=float(stop_row["stop_lat"]),
                    lon=float(stop_row["stop_lon"]),
                    location_type=int(stop_row.get("location_type", 0)),
                    parent_station=parent_station,
                    stop_timezone=stop_timezone,
                )
                self.stops[stop.stop_id] = stop

    def _parse_routes(self) -> None:
        """Parse routes from GTFS data."""
        if self.feed.routes is not None:
            for _, route_row in self.feed.routes.iterrows():
                agency_id = None
                if ("agency_id" in route_row
                    and str(route_row["agency_id"]) != "nan"):
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
                if ("trip_headsign" in trip_row
                    and str(trip_row["trip_headsign"]) != "nan"):
                    trip_headsign = str(trip_row["trip_headsign"])

                direction_id = None
                if ("direction_id" in trip_row
                    and str(trip_row["direction_id"]) != "nan"):
                    direction_id = int(trip_row["direction_id"])

                shape_id = None
                if ("shape_id" in trip_row
                    and str(trip_row["shape_id"]) != "nan"):
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
        if self.feed.stop_times is not None:
            for _, st_row in self.feed.stop_times.iterrows():
                stop_time = StopTime(
                    trip_id=str(st_row["trip_id"]),
                    stop_id=str(st_row["stop_id"]),
                    stop_sequence=int(st_row["stop_sequence"]),
                    arrival_time=str(st_row["arrival_time"]),
                    departure_time=str(st_row["departure_time"]),
                    pickup_type=int(st_row.get("pickup_type", 0)),
                    drop_off_type=int(st_row.get("drop_off_type", 0)),
                )

                if stop_time.trip_id not in self.stop_times:
                    self.stop_times[stop_time.trip_id] = []
                self.stop_times[stop_time.trip_id].append(stop_time)

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

        departures = []
        end_time = start_time + (max_hours * 3600)

        # Convert timestamps to date for service lookup
        start_datetime = datetime.fromtimestamp(start_time)
        service_date = int(
            start_datetime.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()
        )

        # Look through all trips and find those that serve this stop
        for trip_id, stop_times_list in self.stop_times.items():
            if trip_id not in self.trips:
                continue

            trip = self.trips[trip_id]

            # Find stop times for this stop in this trip
            for i, stop_time in enumerate(stop_times_list):
                if stop_time.stop_id != stop_id:
                    continue

                # Skip if this stop doesn't allow pickup
                if stop_time.pickup_type == 1:
                    continue

                # Convert GTFS time to timestamp
                departure_timestamp = gtfs_time_to_timestamp(
                    stop_time.departure_time, service_date
                )
                arrival_timestamp = gtfs_time_to_timestamp(
                    stop_time.arrival_time, service_date
                )

                # Check if departure is within our time window
                if (departure_timestamp < start_time
                    or departure_timestamp > end_time):
                    continue

                # Find next stop in sequence
                next_stop_id = None
                next_stop_sequence = None
                next_arrival_time = None

                if i + 1 < len(stop_times_list):
                    next_stop_time = stop_times_list[i + 1]
                    next_stop_id = next_stop_time.stop_id
                    next_stop_sequence = next_stop_time.stop_sequence
                    next_arrival_time = gtfs_time_to_timestamp(
                        next_stop_time.arrival_time, service_date
                    )

                departure = Departure(
                    trip_id=trip_id,
                    route_id=trip.route_id,
                    stop_id=stop_id,
                    stop_sequence=stop_time.stop_sequence,
                    departure_time=departure_timestamp,
                    arrival_time=arrival_timestamp,
                    next_stop_id=next_stop_id,
                    next_stop_sequence=next_stop_sequence,
                    next_arrival_time=next_arrival_time,
                )
                departures.append(departure)

        # Sort by departure time
        departures.sort(key=lambda d: d.departure_time)
        return departures

    def get_next_stop_in_trip(
        self, trip_id: str, stop_sequence: int
    ) -> StopTime | None:
        """Get the next stop in a trip after the given stop sequence.

        Args:
            trip_id: Trip ID
            stop_sequence: Current stop sequence

        Returns:
            Next stop time or None if no next stop
        """
        if trip_id not in self.stop_times:
            return None

        stop_times_list = self.stop_times[trip_id]

        # Find the next stop with higher sequence number
        for stop_time in stop_times_list:
            if stop_time.stop_sequence > stop_sequence:
                return stop_time

        return None

    def is_service_active(self, service_id: str, date_obj: date) -> bool:  # noqa: ARG002
        """Check if a service is active on a given date.

        Args:
            service_id: Service ID
            date_obj: Date to check

        Returns:
            True if service is active
        """
        # For simplicity, assume all services are active
        # In a real implementation, you would check calendar.txt and calendar_dates.txt
        return True

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
