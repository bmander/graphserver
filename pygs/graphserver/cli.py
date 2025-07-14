import os
import sys

import click

from graphserver.compiler.gdb_import_gtfs import gdb_load_gtfsdb
from graphserver.compiler.gdb_import_ned import get_rise_and_fall
from graphserver.compiler.gdb_import_osm import gdb_import_osm
from graphserver.core import Link, State, Street
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase

try:
    from graphserver.ext.graphcrawler import GraphCrawler

    CRAWL_AVAILABLE = True
except (ImportError, SyntaxError):
    CRAWL_AVAILABLE = False
from graphserver.ext.ned.profile import populate_profile_db
from graphserver.ext.osm.osmdb import OSMDB, osm_to_osmdb
from graphserver.ext.osm.osmfilters import OSMDBFilter
from graphserver.ext.osm.profiledb import ProfileDB
from graphserver.ext.routeserver.routeserver import create_app
from graphserver.graphdb import GraphDatabase
from graphserver.vincenty import vincenty


@click.group()
def cli():
    """Graphserver command line utility."""


@cli.group()
def compile():
    """Compile data into Graphserver databases."""


@compile.command()
@click.argument("gtfs_filename")
@click.argument("gtfsdb_filename")
@click.option(
    "-t", "--table", "tables", multiple=True, help="Copy only the given tables"
)
@click.option("-v", "--verbose", is_flag=True, help="Increase output verbosity")
def gtfs(gtfs_filename, gtfsdb_filename, tables, verbose):
    """Compile a GTFS zip file into a GTFS database."""
    if not tables:
        tables = None
    gtfsdb = GTFSDatabase(gtfsdb_filename, overwrite=True)
    gtfsdb.load_gtfs(gtfs_filename, tables, reporter=sys.stdout, verbose=verbose)


@compile.command()
@click.argument("args", nargs=-1)
@click.option("-t", "--tolerant", is_flag=True, help="Allow invalid geometries")
@click.option("-d", "--dryrun", is_flag=True, help="Read OSM but do not write to DB")
def osm(args, tolerant, dryrun):
    """Compile one or more OSM files into an OSM database."""
    if len(args) < 2:
        raise click.UsageError("OSM file(s) and destination database required")
    *osm_files, osmdb_filename = args
    osm_to_osmdb(osm_files, osmdb_filename, tolerant, dryrun)


@compile.command()
@click.argument("osmdb_filename")
@click.argument("profiledb_filename")
@click.argument("resolution", type=int)
@click.argument("dem_basenames", nargs=-1, required=True)
def profile(osmdb_filename, profiledb_filename, resolution, dem_basenames):
    """Compile elevation profiles from DEM data into a profile database."""
    click.echo(f"osmdb name: {osmdb_filename}")
    click.echo(f"profiledb name: {profiledb_filename}")
    click.echo(f"resolution: {resolution}")
    click.echo(f"dem_basenames: {dem_basenames}")

    populate_profile_db(osmdb_filename, profiledb_filename, dem_basenames, resolution)


@cli.command()
@click.argument("graphdb_filename")
@click.option("-o", "--overwrite", is_flag=True, help="Overwrite existing database")
def new(graphdb_filename, overwrite):
    """Create a new empty graph database."""
    if not os.path.exists(graphdb_filename) or overwrite:
        click.echo(f"Creating graph database '{graphdb_filename}'")
        GraphDatabase(graphdb_filename, overwrite=overwrite)
    else:
        click.echo(
            f"Graph database '{graphdb_filename}' already exists. Use -o to overwrite"
        )


@cli.group(name="import")
def import_cmd():
    """Import compiled data into a graph database."""


@cli.group()
def show():
    """Show information about databases."""


@cli.group()
def filter():
    """Filter and process databases."""


@filter.command()
@click.argument("filter_name")
@click.argument("mode", type=click.Choice(["run", "rerun", "visualize"]))
@click.argument("osmdb_file")
@click.argument("filter_args", nargs=-1)
def osm(filter_name, mode, osmdb_file, filter_args):
    """Filter and process OSM databases."""
    # Import the osmfilters module to get access to all filter classes
    import graphserver.ext.osm.osmfilters as osmfilters

    # Get all filter classes
    available_filters = {}
    for name, obj in vars(osmfilters).items():
        if (
            isinstance(obj, type)
            and issubclass(obj, OSMDBFilter)
            and obj != OSMDBFilter
        ):
            available_filters[name] = obj

    if filter_name not in available_filters:
        click.echo(f"Filter '{filter_name}' not found. Available filters:")
        for name in available_filters:
            click.echo(f" -- {name}")
        raise click.Abort()

    filter_cls = available_filters[filter_name]
    filter_instance = filter_cls()

    db = OSMDB(osmdb_file)

    if mode == "run":
        filter_instance.run(db, *filter_args)
    elif mode == "rerun":
        filter_instance.rerun(db, *filter_args)
    elif mode == "visualize":
        filter_instance.visualize(db, *filter_args)


@show.command()
@click.argument("gtfsdb_filename")
@click.argument("query", required=False)
def gtfsdb(gtfsdb_filename, query):
    """Show information about a GTFS database."""
    gtfsdb = GTFSDatabase(gtfsdb_filename)

    if query is None:
        for table_name, fields in gtfsdb.GTFS_DEF:
            click.echo(f"Table: {table_name}")
            for field_name, field_type, field_converter in fields:
                click.echo(f"\t{field_type} {field_name}")
    else:
        for record in gtfsdb.execute(query):
            click.echo(record)


@show.command()
@click.argument("graphdb_filename")
@click.argument("vertex1", required=False)
@click.argument("time", required=False, type=int)
def gdb(graphdb_filename, vertex1, time):
    """Show information about a graph database."""
    gdb = GraphDatabase(graphdb_filename)

    if vertex1 is None:
        click.echo("vertices:")
        for vertex_label in sorted(gdb.all_vertex_labels()):
            click.echo(vertex_label)
        click.echo("resources:")
        for name, resource in gdb.resources():
            click.echo(f"{name} {resource}")
    else:
        for v1, v2, edgetype in gdb.all_outgoing(vertex1):
            click.echo(f"{v1} -> {v2}\n\t{repr(edgetype)}")

            if time is not None:
                s0 = State(1, time)
                result = edgetype.walk(s0)
                click.echo(f"\t{str(result)}")


@import_cmd.command(name="osm")
@click.argument("graphdb_filename")
@click.argument("osmdb_filename")
@click.option("-n", "--namespace", default="osm", help="Vertex namespace prefix")
@click.option(
    "-s",
    "--slog",
    "slog_strings",
    multiple=True,
    help="Highway slog in type:value form",
)
@click.option(
    "-p",
    "--profiledb",
    "profiledb_filename",
    default=None,
    help="ProfileDB with rise/fall data",
)
def import_osm(
    graphdb_filename, osmdb_filename, namespace, slog_strings, profiledb_filename
):
    """Import an OSM database into a graph database."""
    slogs = {}
    for slog_string in slog_strings:
        highway_type, slog_penalty = slog_string.split(":")
        slogs[highway_type] = float(slog_penalty)
    profiledb = ProfileDB(profiledb_filename) if profiledb_filename else None
    osmdb = OSMDB(osmdb_filename)
    gdb = GraphDatabase(graphdb_filename, overwrite=False)
    gdb_import_osm(gdb, osmdb, namespace, slogs, profiledb)


@import_cmd.command(name="gtfs")
@click.argument("graphdb_filename")
@click.argument("gtfsdb_filename")
@click.argument("agency_id", required=False)
@click.option("-n", "--namespace", default="0", help="Agency namespace")
@click.option("-m", "--maxtrips", default=None, help="Maximum number of trips to load")
@click.option(
    "-d",
    "--date",
    "sample_date",
    default=None,
    help="Only load transit running on YYYYMMDD",
)
def import_gtfs(
    graphdb_filename, gtfsdb_filename, agency_id, namespace, maxtrips, sample_date
):
    """Import a GTFS database into a graph database."""
    gtfsdb = GTFSDatabase(gtfsdb_filename)
    gdb = GraphDatabase(graphdb_filename, overwrite=False)
    maxtrips_int = int(maxtrips) if maxtrips else None
    gdb_load_gtfsdb(
        gdb,
        namespace,
        gtfsdb,
        gdb.get_cursor(),
        agency_id,
        maxtrips=maxtrips_int,
        sample_date=sample_date,
    )
    gdb.commit()


@import_cmd.command(name="ned")
@click.argument("graphdb_filename")
@click.argument("profiledb_filename")
def import_ned(graphdb_filename, profiledb_filename):
    """Import NED elevation data into a graph database."""
    gdb = GraphDatabase(graphdb_filename)
    profiledb = ProfileDB(profiledb_filename)

    n = gdb.num_edges()

    for i, (oid, vertex1, vertex2, edge) in enumerate(
        list(gdb.all_edges(include_oid=True))
    ):
        if i % 500 == 0:
            click.echo(f"{i}/{n}")

        if isinstance(edge, Street):
            rise, fall = get_rise_and_fall(profiledb.get(edge.name))
            edge.rise = rise
            edge.fall = fall

            gdb.remove_edge(oid)
            gdb.add_edge(vertex1, vertex2, edge)


@cli.command()
@click.argument("graphdb_filename")
@click.option("--osm-file", "osm_file", help="OSM database filename")
@click.option(
    "--gtfs-file", "gtfs_files", multiple=True, help="GTFS database filename(s)"
)
@click.option("--range", "link_range", type=float, help="Range for GTFS-GTFS linking")
def link(graphdb_filename, osm_file, gtfs_files, link_range):
    """Link vertices in a graph database."""
    if osm_file and len(gtfs_files) == 1:
        # OSM-GTFS linking
        gtfsdb_filename = gtfs_files[0]
        gtfsdb = GTFSDatabase(gtfsdb_filename)
        osmdb = OSMDB(osm_file)
        gdb = GraphDatabase(graphdb_filename)

        n_stops = gtfsdb.count_stops()
        c = gdb.get_cursor()
        for i, (stop_id, _name, stop_lat, stop_lon) in enumerate(gtfsdb.stops()):
            click.echo(f"{i}/{n_stops}")

            nd_id, nd_lat, nd_lon, nd_dist = osmdb.nearest_node(stop_lat, stop_lon)
            station_vertex_id = f"sta-{stop_id}"
            osm_vertex_id = f"osm-{nd_id}"

            click.echo(f"{station_vertex_id} {osm_vertex_id}")

            gdb.add_edge(station_vertex_id, osm_vertex_id, Link(), c)
            gdb.add_edge(osm_vertex_id, station_vertex_id, Link(), c)

        gdb.commit()

    elif len(gtfs_files) == 2:
        # GTFS-GTFS linking
        if link_range is None:
            raise click.UsageError("--range is required for GTFS-GTFS linking")

        gtfsdb_filename = gtfs_files[0]  # Use first GTFS file as source
        gtfsdb = GTFSDatabase(gtfsdb_filename)
        gdb = GraphDatabase(graphdb_filename)

        n_stops = gtfsdb.count_stops()

        for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate(gtfsdb.stops()):
            click.echo(f"{i}/{n_stops} {stop_id}")

            station_vertex_id = f"sta-{stop_id}"

            for (
                link_stop_id,
                link_stop_name,
                link_stop_lat,
                link_stop_lon,
            ) in gtfsdb.nearby_stops(stop_lat, stop_lon, link_range):
                if link_stop_id == stop_id:
                    continue

                click.echo(".")

                link_length = vincenty(stop_lat, stop_lon, link_stop_lat, link_stop_lon)
                link_station_vertex_id = f"sta-{link_stop_id}"
                gdb.add_edge(
                    station_vertex_id,
                    link_station_vertex_id,
                    Street("link", link_length),
                )

            click.echo("")

    else:
        raise click.UsageError(
            "Provide either: --osm-file and one --gtfs-file, or two --gtfs-file arguments"
        )


@cli.command()
@click.argument("graphdb_filename")
@click.option("-p", "--port", default=8081, help="Port to serve on")
def crawl(graphdb_filename, port):
    """Start a web server for crawling graph databases."""
    if not CRAWL_AVAILABLE:
        click.echo(
            "Error: GraphCrawler not available due to servable dependency issues"
        )
        click.echo("See: https://github.com/bmander/graphserver/issues/42")
        raise click.Abort()

    gc = GraphCrawler(graphdb_filename)
    click.echo(f"serving on port {port}")
    gc.run_test_server(port=port)


@cli.command()
@click.argument("graphdb_filename")
@click.argument("config_filename")
@click.option("-p", "--port", default=8080, type=int, help="Port to serve HTTP")
def routeserver(graphdb_filename, config_filename, port):
    """Start a route server for path planning."""
    app = create_app(graphdb_filename, config_filename)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    cli()
