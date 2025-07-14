import os
import sys

import click

from graphserver.compiler.gdb_import_gtfs import gdb_load_gtfsdb
from graphserver.compiler.gdb_import_osm import gdb_import_osm
from graphserver.core import Link
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.graphcrawler import GraphCrawler
from graphserver.ext.osm.osmdb import OSMDB, osm_to_osmdb
from graphserver.ext.osm.profiledb import ProfileDB
from graphserver.graphdb import GraphDatabase


@click.group()
def cli():
    """Graphserver command line utility."""


@cli.group()
def compile():
    """Compile data into Graphserver databases."""


@compile.command()
@click.argument("gtfs_filename")
@click.argument("gtfsdb_filename")
@click.option("-t", "--table", "tables", multiple=True, help="Copy only the given tables")
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


@import_cmd.command(name="osm")
@click.argument("graphdb_filename")
@click.argument("osmdb_filename")
@click.option("-n", "--namespace", default="osm", help="Vertex namespace prefix")
@click.option("-s", "--slog", "slog_strings", multiple=True, help="Highway slog in type:value form")
@click.option("-p", "--profiledb", "profiledb_filename", default=None, help="ProfileDB with rise/fall data")
def import_osm(graphdb_filename, osmdb_filename, namespace, slog_strings, profiledb_filename):
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
@click.option("-d", "--date", "sample_date", default=None, help="Only load transit running on YYYYMMDD")
def import_gtfs(graphdb_filename, gtfsdb_filename, agency_id, namespace, maxtrips, sample_date):
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


@cli.command()
@click.argument("graphdb_filename")
@click.argument("osmdb_filename")
@click.argument("gtfsdb_filename")
def link(graphdb_filename, osmdb_filename, gtfsdb_filename):
    """Link OSM vertices to GTFS vertices."""
    gtfsdb = GTFSDatabase(gtfsdb_filename)
    osmdb = OSMDB(osmdb_filename)
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


@cli.command()
@click.argument("graphdb_filename")
@click.option("-p", "--port", default=8081, help="Port to serve on")
def crawl(graphdb_filename, port):
    """Start a web server for crawling graph databases."""
    gc = GraphCrawler(graphdb_filename)
    click.echo(f"serving on port {port}")
    gc.run_test_server(port=port)


if __name__ == "__main__":
    cli()
