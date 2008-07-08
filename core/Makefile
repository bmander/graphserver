
all: libgraphserver

# You know what? Honestly? I don't know what most of these switches do.
libgraphserver: dirfibheap edgetypes hashtable_itr fibheap statetypes dirfibheap graph edgetypes hashtable_gs hashtable_utility hashtable
	cc -shared -o libgraphserver.so hashtable_itr.o  fibheap.o statetypes.o dirfibheap.o graph.o edgetypes.o hashtable_gs.o hashtable_utility.o hashtable.o -L. -Bsymbolic-functions -rdynamic -Wall -export-dynamic -liberty -ldl -lcrypt -lm -lc

dirfibheap: dirfibheap.c dirfibheap.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c dirfibheap.c

edgetypes: edgetypes.c edgeweights.c edgetypes.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c edgetypes.c

hashtable_itr: hashtable_itr.c hashtable_itr.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c hashtable_itr.c

fibheap: fibheap.c fibheap.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c fibheap.c

statetypes: statetypes.c statetypes.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c statetypes.c

graph: graph.c graph.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c graph.c

hashtable_gs: hashtable_gs.c hashtable_gs.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c hashtable_gs.c

hashtable_utility: hashtable_utility.c hashtable_utility.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c hashtable_utility.c

hashtable: hashtable.c hashtable.h
	cc -I. -g -fno-strict-aliasing -O2 -fPIC -Wall -c hashtable.c

install:
	cp libgraphserver.so /usr/lib
	mkdir -p /usr/include/graphserver
	cp fibheap.h /usr/include/graphserver
	cp dirfibheap.h /usr/include/graphserver
	cp graph.h /usr/include/graphserver
	cp hashtable_gs.h /usr/include/graphserver
	cp hashtable_itr.h /usr/include/graphserver
	cp edgetypes.h /usr/include/graphserver
	cp hashtable.h /usr/include/graphserver
	cp hashtable_utility.h /usr/include/graphserver
	cp hashtable_private.h /usr/include/graphserver
	cp statetypes.h /usr/include/graphserver