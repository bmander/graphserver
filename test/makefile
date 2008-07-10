all: streetprofile
streetprofile: testsetparent.c streetprofile.c testdestroystates.c thsprofile.c ../core/libgraphserver.so
	cc -g streetprofile.c ../core/libgraphserver.so -o streetprofile -lm -liberty
	cc -g testsetparent.c ../core/libgraphserver.so -o testsetparent -lm -liberty
	cc -g testdestroystates.c ../core/libgraphserver.so -o testdestroystates -lm -liberty
	cc -g thsprofile.c ../core/libgraphserver.so -o thsprofile -lm -liberty