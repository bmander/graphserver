all: streetprofile
streetprofile: testsetparent.c streetprofile.c testdestroystates.c ../../core/graph_core.so
	cc -g streetprofile.c ../../core/graph_core.so -o streetprofile -lm -liberty
	cc -g testsetparent.c ../../core/graph_core.so -o testsetparent -lm -liberty
	cc -g testdestroystates.c ../../core/graph_core.so -o testdestroystates -lm -liberty