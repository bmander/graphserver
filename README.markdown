# GRAPHSERVER

## OVERVIEW 

Graphserver is a multi-modal trip planner. Graphserver supports transit modes
through GTFS, and street-based modes through OSM.

The core graphserver library has Python bindings which provide easy construction, 
storage, and analysis of graph objects.

Learn more about Graphserver at [http://graphserver.github.com/graphserver/](http://graphserver.github.com/graphserver/)

## INSTALLATION

### Build

**Note: The build process requires two steps to resolve linking issues with inline functions.**

#### Step 1: Build the core C library
```bash
    $ cd core
    $ make
    $ sudo make install
```

#### Step 2: Install Python bindings
```bash
cd pygs
pip install .
```

**For development installation (editable):**
```bash
cd pygs
pip install -e .
```

This installs the Python package and command-line tools. The tools are installed to your Python environment's bin directory.

### Verification

After successful installation, verify all components work:

```bash
# Test core import
python3 -c "import graphserver.core; print('Core module: OK')"

# Test graph creation
python3 -c "import graphserver.core; g = graphserver.core.Graph(); print('Graph creation: OK')"

# Check installed tools
which gs_new gs_import_osm gs_import_gtfs
```

## TOOLS

#### gs_gtfsdb_compile
Create a GTFSDatabase (sqlite3 db) from a GTFS zip file
    $ gs_gtfsdb_compile google_transit.zip google_transit.gtfsdb

#### gs_osmdb_compile
Create a OSM database (sqlite3 db) from an OSM xml file
    $ gs_osmdb_compile map.osm map.osmdb

#### gs_new
Create a new graph file
    $ gs_new foobar.gdb

#### gs_import_osm
Import an OSM database to a graph file
    $ gs_import_osm foobar.gdb map.osmdb

#### gs_import_gtfs
Import a GTFS database to a graph file
    $ gs_import_gtfs foobar.gdb google_transit.gtfsdb

#### gs_link_osm_gtfs
Link OSM vertices to GTFS vertices to enable multimodal trip planning
    $ gs_link_osm_gtfs foobar.gdb map.osmdb google_transit.gtfsdb

#### gs_osmfilter: run one of the filter classes from graphserver.ext.osm.osmfilters on an OSMDB instance
    $ gs_osmfilter <Filter Name> <run|rerun|visualize> <osmdb_file> [<filter args> ...]
   
## Building just the C .dll/.so

Provides the core DLL for routing. It is not necessary to manually build this if
using the Python bindings.

Build:
    $ cd core
    $ make

Install:
    $ cd core
    $ sudo make install

