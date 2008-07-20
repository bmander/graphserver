from distutils.core import setup
import os.path, sys

LIBSO = 'core/libgraphserver.so'

if not os.path.exists(LIBSO):
    print "ERROR: %s not found.  Have you run '(cd core && make)' yet?" % LIBSO
    sys.exit(-1)


setup( name='graphserver',
       version='0.1',
       url='http://graphserver.wiki.sourceforge.net/',
       py_modules=['pygs.gsdll', 'pygs.graphserver', 'pygs.engine', 'pygs.server', 'pygs.ext', 'pygs.ext.osm',
                   'pygs.ext.osm.osm', 'pygs.ext.osm.graph', 'pygs.ext.osm.server', 'pygs.ext.osm.load_osm'],
       data_files=[('/usr/lib',[LIBSO])])