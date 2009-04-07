from setuptools import setup, find_packages
import os.path, sys, subprocess

LIBSO = os.path.join('..','core','libgraphserver.so')

# build and copy libgraphserver.so
subprocess.call(["make","-s", "-C","../core"])
subprocess.call(["cp",LIBSO,"graphserver/"])

setup(  name='graphserver',
        version='0.1',
        packages = find_packages(exclude=['examples.*','examples','test','test.*']),
        install_requires=['pytz>=2008b','pyproj>=1.8.5','servable>=2009b'], 
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
        package_data = {'graphserver':['libgraphserver.so']}  )
