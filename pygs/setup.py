from distutils.core import setup

import os.path, sys



LIBSO = '../core/libgraphserver.so'



if not os.path.exists(LIBSO):

    print "ERROR: %s not found.  Have you run '(cd core && make)' yet?" % LIBSO

    sys.exit(-1)



"""py_modules=['graphserver.gsdll', 'graphserver.core', 'graphserver.engine', 'graphserver.util', 'graphserver.ext', 'graphserver.ext.osm', 'graphserver.ext.gtfs', 'graphserver.ext.gtfs.load_gtfs',

                   'graphserver.ext.osm.osm', 'graphserver.ext.osm.graph', 'graphserver.ext.osm.engine', 'graphserver.ext.osm.load_osm'],"""

setup( name='graphserver',

       version='0.1',

       url='http://graphserver.wiki.sourceforge.net/',

       packages = ['graphserver.ext'],

       py_modules=['graphserver.gsdll', 

                   'graphserver.core', 

                   'graphserver.engine', 

                   'graphserver.util',

                   'graphserver.graphdb',

                   'graphserver.ext.gtfs.load_gtfs',

                   'graphserver.ext.gtfs.gtfsdb',

                   'graphserver.ext.osm.osm', 

                   'graphserver.ext.osm.vincenty',

                   'graphserver.ext.osm.graph', 

                   'graphserver.ext.osm.engine', 

                   'graphserver.ext.osm.load_osm',

                   'graphserver.ext.osm.osmdb',],

       data_files=[('/usr/lib',[LIBSO])])