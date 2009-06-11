from setuptools import setup, find_packages
import os.path, sys, subprocess

LIBSO = os.path.join('..','core','libgraphserver.so')

# build and copy libgraphserver.so
subprocess.call(["make","-s", "-C","../core"])
subprocess.call(["cp",LIBSO,"graphserver/"])

setup(  name='graphserver',
        version='0.1',
        packages = find_packages(exclude=['examples.*','examples','test','test.*']),
        install_requires=['pytz>=2008b','pyproj>=1.8.5','servable>=2009b','nose>=0.10.4'], 
        zip_safe=False,
        extras_require = {
        #    'transitfeed':  ["transitfeed>=1.1.6"],
        },
        
        test_suite='nose.collector',
        
        # metadata for upload to PyPI
        author = "Brandon Martin-Anderson",
        author_email = "badhill@gmail.com",
        description = "Graphserver routing engine.",
        license = "BSD",
        keywords = "OSM OpenStreetMap GTFS routing transit",
        url = "http://github.com/bmander/graphserver/tree/master",
        
        # put libgraphserver.so next to gsdll.py
        package_data = {'graphserver':['libgraphserver.so']} ,
        
        entry_points = {
            'console_scripts': [
                'gs_compile_gdb = graphserver.compiler.compile_graph:main',
                'gs_osmfilter = graphserver.ext.osm.osmfilters:main',
                'gs_osmdb_compile = graphserver.ext.osm.osmdb:main',
                'gs_gtfsdb_build = graphserver.ext.gtfs.gtfsdb:main_build_gtfsdb',
                'gs_gtfsdb_inspect = graphserver.ext.gtfs.gtfsdb:main_inspect_gtfsdb',
                'gs_crawl = graphserver.ext.graphcrawler:main',
            ],
            #'setuptools.installation': ['eggsecutable = umigis.server.setup:main']
        }
        
)
