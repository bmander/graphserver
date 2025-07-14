import datetime
from optparse import OptionParser
import sys

from graphserver.core import (
    Crossing,
    ElapseTime,
    Graph,
    HeadwayAlight,
    HeadwayBoard,
    Link,
    Timezone,
    TripAlight,
    TripBoard,
)
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase, parse_gtfs_date
from graphserver.graphdb import GraphDatabase

from .tools import service_calendar_from_timezone


def cons(ary):
    for i in range(len(ary) - 1):
        yield (ary[i], ary[i + 1])


class GTFSGraphCompiler:
    def __init__(self, gtfsdb, agency_namespace, agency_id=None, reporter=None):
        self.gtfsdb = gtfsdb
        self.agency_namespace = agency_namespace
        self.reporter = reporter

        # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
        timezone_name = gtfsdb.agency_timezone_name(agency_id)
        self.tz = Timezone.generate(timezone_name)
        if reporter:
            reporter.write(
                "constructing service calendar for timezone '%s'\n" % timezone_name
            )
        self.sc = service_calendar_from_timezone(gtfsdb, timezone_name)

    def bundle_to_boardalight_edges(self, bundle, service_id):
        """takes a bundle and yields a bunch of edges"""

        stop_time_bundles = bundle.stop_time_bundles(service_id)

        n_trips = len(bundle.trip_ids)

        # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
        if len(stop_time_bundles) < 2:
            return

        # If there are no stop_times in a bundle on this service day, there is nothing to load
        if n_trips == 0:
            return

        if self.reporter:
            self.reporter.write(
                "inserting %d trips with %d stop_time bundles on service_id '%s'\n"
                % (len(stop_time_bundles[0]), len(stop_time_bundles), service_id)
            )

        # add board edges
        for i, stop_time_bundle in enumerate(stop_time_bundles[:-1]):
            (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) = stop_time_bundle[0]

            if arrival_time != departure_time:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i,
                    service_id,
                )

                # construct the board/alight/dwell triangle for this patternstop
                patternstop_arrival_vx_name = "psv-%s-%03d-%03d-%s-arrive" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i,
                    service_id,
                )

                dwell_crossing = Crossing()
                for (
                    trip_id,
                    arrival_time,
                    departure_time,
                    stop_id,
                    stop_sequence,
                    stop_dist_traveled,
                ) in stop_time_bundle:
                    dwell_crossing.add_crossing_time(
                        trip_id, departure_time - arrival_time
                    )

                yield (patternstop_arrival_vx_name, patternstop_vx_name, dwell_crossing)

            else:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i,
                    service_id,
                )

            b = TripBoard(service_id, self.sc, self.tz, 0)
            for (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) in stop_time_bundle:
                b.add_boarding(trip_id, departure_time, stop_sequence)

            yield ("sta-%s" % stop_id, patternstop_vx_name, b)

        # add alight edges
        for i, stop_time_bundle in enumerate(stop_time_bundles[1:]):
            (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) = stop_time_bundle[0]

            if arrival_time != departure_time:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i + 1,
                    service_id,
                )
            else:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i + 1,
                    service_id,
                )

            al = TripAlight(service_id, self.sc, self.tz, 0)
            for (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) in stop_time_bundle:
                al.add_alighting(trip_id.encode("ascii"), arrival_time, stop_sequence)

            yield (patternstop_vx_name, "sta-%s" % stop_id, al)

        # add crossing edges
        for i, (from_stop_time_bundle, to_stop_time_bundle) in enumerate(
            cons(stop_time_bundles)
        ):
            (
                trip_id,
                from_arrival_time,
                from_departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) = from_stop_time_bundle[0]
            (
                trip_id,
                to_arrival_time,
                to_departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) = to_stop_time_bundle[0]

            if from_arrival_time != from_departure_time:
                from_patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i,
                    service_id,
                )
            else:
                from_patternstop_vx_name = "psv-%s-%03d-%03d-%s" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i,
                    service_id,
                )

            if to_arrival_time != to_departure_time:
                to_patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i + 1,
                    service_id,
                )
            else:
                to_patternstop_vx_name = "psv-%s-%03d-%03d-%s" % (
                    self.agency_namespace,
                    bundle.pattern.pattern_id,
                    i + 1,
                    service_id,
                )

            crossing = Crossing()
            for i in range(len(from_stop_time_bundle)):
                (
                    trip_id,
                    from_arrival_time,
                    from_departure_time,
                    stop_id,
                    stop_sequence,
                    stop_dist_traveled,
                ) = from_stop_time_bundle[i]
                (
                    trip_id,
                    to_arrival_time,
                    to_departure_time,
                    stop_id,
                    stop_sequence,
                    stop_dist_traveled,
                ) = to_stop_time_bundle[i]
                crossing.add_crossing_time(
                    trip_id, (to_arrival_time - from_departure_time)
                )

            yield (from_patternstop_vx_name, to_patternstop_vx_name, crossing)

    def gtfsdb_to_scheduled_edges(self, maxtrips=None, service_ids=None):
        # compile trip bundles from gtfsdb
        if self.reporter:
            self.reporter.write("Compiling trip bundles...\n")
        bundles = self.gtfsdb.compile_trip_bundles(
            maxtrips=maxtrips, reporter=self.reporter
        )

        # load bundles to graph
        if self.reporter:
            self.reporter.write("Loading trip bundles into graph...\n")
        n_bundles = len(bundles)
        for i, bundle in enumerate(bundles):
            if self.reporter:
                self.reporter.write("%d/%d loading %s\n" % (i + 1, n_bundles, bundle))

            for service_id in [x.encode("ascii") for x in self.gtfsdb.service_ids()]:
                if service_ids is not None and service_id not in service_ids:
                    continue

                for fromv_label, tov_label, edge in self.bundle_to_boardalight_edges(
                    bundle, service_id
                ):
                    yield fromv_label, tov_label, edge

    def gtfsdb_to_headway_edges(self, maxtrips=None):
        # load headways
        if self.reporter:
            self.reporter.write("Loading headways trips to graph...\n")
        for trip_id, start_time, end_time, headway_secs in self.gtfsdb.execute(
            "SELECT * FROM frequencies"
        ):
            service_id = list(
                self.gtfsdb.execute(
                    "SELECT service_id FROM trips WHERE trip_id=?", (trip_id,)
                )
            )[0][0]
            service_id = service_id.encode("utf-8")

            hb = HeadwayBoard(
                service_id,
                self.sc,
                self.tz,
                0,
                trip_id.encode("utf-8"),
                start_time,
                end_time,
                headway_secs,
            )
            ha = HeadwayAlight(
                service_id,
                self.sc,
                self.tz,
                0,
                trip_id.encode("utf-8"),
                start_time,
                end_time,
                headway_secs,
            )

            stoptimes = list(
                self.gtfsdb.execute(
                    "SELECT * FROM stop_times WHERE trip_id=? ORDER BY stop_sequence",
                    (trip_id,),
                )
            )

            # add board edges
            for (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) in stoptimes[:-1]:
                yield (
                    "sta-%s" % stop_id,
                    "hwv-%s-%s-%s" % (self.agency_namespace, stop_id, trip_id),
                    hb,
                )

            # add alight edges
            for (
                trip_id,
                arrival_time,
                departure_time,
                stop_id,
                stop_sequence,
                stop_dist_traveled,
            ) in stoptimes[1:]:
                yield (
                    "hwv-%s-%s-%s" % (self.agency_namespace, stop_id, trip_id),
                    "sta-%s" % stop_id,
                    ha,
                )

            # add crossing edges
            for (
                trip_id1,
                arrival_time1,
                departure_time1,
                stop_id1,
                stop_sequence1,
                stop_dist_traveled1,
            ), (
                trip_id2,
                arrival_time2,
                departure_time2,
                stop_id2,
                stop_sequence2,
                stop_dist_traveled2,
            ) in cons(stoptimes):
                cr = Crossing()
                cr.add_crossing_time(trip_id1, (arrival_time2 - departure_time1))
                yield (
                    "hwv-%s-%s-%s" % (self.agency_namespace, stop_id1, trip_id1),
                    "hwv-%s-%s-%s" % (self.agency_namespace, stop_id2, trip_id2),
                    cr,
                )

    def gtfsdb_to_transfer_edges(self):
        # load transfers
        if self.reporter:
            self.reporter.write("Loading transfers to graph...\n")

        # keep track to avoid redundancies
        # this assumes that transfer relationships are bi-directional.
        # TODO this implementation is also incomplete - it's theoretically possible that
        # a transfers.txt table could contain "A,A,3,", which would mean you can't transfer
        # at A.
        seen = set([])
        for stop_id1, stop_id2, conn_type, min_transfer_time in self.gtfsdb.execute(
            "SELECT * FROM transfers"
        ):
            s1 = "sta-%s" % stop_id1
            s2 = "sta-%s" % stop_id2

            # TODO - what is the semantics of this? see note above
            if s1 == s2:
                continue

            key = ".".join(sorted([s1, s2]))
            if key not in seen:
                seen.add(key)
            else:
                continue

            assert conn_type is None or isinstance(conn_type, int)
            if conn_type in (
                0,
                None,
            ):  # This is a recommended transfer point between two routes
                if min_transfer_time in ("", None):
                    yield (s1, s2, Link())
                    yield (s2, s1, Link())
                else:
                    yield (s1, s2, ElapseTime(int(min_transfer_time)))
                    yield (s2, s1, ElapseTime(int(min_transfer_time)))
            elif conn_type == 1:  # This is a timed transfer point between two routes
                yield (s1, s2, Link())
                yield (s2, s1, Link())
            elif conn_type == 2:  # This transfer requires a minimum amount of time
                yield (s1, s2, ElapseTime(int(min_transfer_time)))
                yield (s2, s1, ElapseTime(int(min_transfer_time)))
            elif (
                conn_type == 3
            ):  # Transfers are not possible between routes at this location.
                print(
                    "WARNING: Support for no-transfer (transfers.txt transfer_type=3) not implemented."
                )

    def gtfsdb_to_edges(self, maxtrips=None, service_ids=None):
        for edge_tuple in self.gtfsdb_to_scheduled_edges(
            maxtrips, service_ids=service_ids
        ):
            yield edge_tuple

        for edge_tuple in self.gtfsdb_to_headway_edges(maxtrips):
            yield edge_tuple

        for edge_tuple in self.gtfsdb_to_transfer_edges():
            yield edge_tuple


def gdb_load_gtfsdb(
    gdb,
    agency_namespace,
    gtfsdb,
    cursor,
    agency_id=None,
    maxtrips=None,
    sample_date=None,
    reporter=sys.stdout,
):
    # determine which service periods run on the given day, if a day is given
    if sample_date is not None:
        sample_date = datetime.date(*parse_gtfs_date(sample_date))
        acceptable_service_ids = gtfsdb.service_periods(sample_date)
        print(
            "Importing only service periods operating on %s: %s"
            % (sample_date, acceptable_service_ids)
        )
    else:
        acceptable_service_ids = None

    compiler = GTFSGraphCompiler(gtfsdb, agency_namespace, agency_id, reporter)
    c = gdb.get_cursor()
    v_added = set([])
    for fromv_label, tov_label, edge in compiler.gtfsdb_to_edges(
        maxtrips, service_ids=acceptable_service_ids
    ):
        if fromv_label not in v_added:
            gdb.add_vertex(fromv_label, c)
            v_added.add(fromv_label)
        if tov_label not in v_added:
            gdb.add_vertex(tov_label, c)
            v_added.add(tov_label)
        gdb.add_edge(fromv_label, tov_label, edge, c)
    gdb.commit()


def graph_load_gtfsdb(
    agency_namespace, gtfsdb, agency_id=None, maxtrips=None, reporter=sys.stdout
):
    compiler = GTFSGraphCompiler(gtfsdb, agency_namespace, agency_id, reporter)

    gg = Graph()

    for fromv_label, tov_label, edge in compiler.gtfsdb_to_edges(maxtrips):
        gg.add_vertex(fromv_label)
        gg.add_vertex(tov_label)
        gg.add_edge(fromv_label, tov_label, edge)

    return gg
