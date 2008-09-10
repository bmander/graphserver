from distutils.core import setup
import os.path, sys

LIBSO = '../core/libgraphserver.so'

if not os.path.exists(LIBSO):
    print "ERROR: %s not found.  Have you run '(cd core && make)' yet?" % LIBSO
    sys.exit(-1)


setup( name='graphserver',
       version='0.1',
       url='http://graphserver.wiki.sourceforge.net/',
       py_modules=['graphserver.gsdll', 'graphserver.core', 'graphserver.engine', 'graphserver.util', 'graphserver.ext', 'graphserver.ext.osm', 'graphserver.ext.gtfs', 'graphserver.ext.gtfs.load_gtfs',
                   'graphserver.ext.osm.osm', 'graphserver.ext.osm.graph', 'graphserver.ext.osm.engine', 'graphserver.ext.osm.load_osm'],
       data_files=[('/usr/lib',[LIBSO])])