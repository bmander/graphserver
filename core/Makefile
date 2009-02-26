all: libgraphserver.so

# to override base installation directory run
# PREFIX=... make install
PREFIX=/usr

OBJECTS= dirfibheap.o \
	edgetypes.o \
	fibheap.o \
	graph.o \
	hashtable.o \
	hashtable_gs.o \
	hashtable_itr.o \
	hashtable_utility.o \
	statetypes.o 

# You know what? Honestly? I don't know what most of these switches do.
CFLAGS=-g -fno-strict-aliasing -O2 -fPIC -Wall
LDFLAGS= -L. -Bsymbolic-functions -rdynamic -Wall -export-dynamic -ldl \
	 -lcrypt -lm -lc

# This complicated-looking rule will autogenerate the appropriate dependancies
# for each source file, ensuring that they are recompiled when the headers
# they include change
# see: http://www.cs.berkeley.edu/~smcpeak/autodepend/autodepend.html
%.o: %.c
	cc $*.c -c -o $@ $(CFLAGS)
	cc $*.c -MM $(CFLAGS) > $*.d
	@mv -f $*.d $*.d.tmp
	@sed -e 's|.*:|$*.o:|' < $*.d.tmp > $*.d
	@sed -e 's/.*://' -e 's/\\$$//' < $*.d.tmp | fmt -1 | \
	  sed -e 's/^ *//' -e 's/$$/:/' >> $*.d
	@rm -f $*.d.tmp
-include $(OBJECTS:.o=.d)

libgraphserver.so: $(OBJECTS)
	cc -shared -o $@ $(OBJECTS) $(LDFLAGS)

install:
	cp libgraphserver.so $(PREFIX)/lib
	mkdir -p $(PREFIX)/include/graphserver
	cp fibheap.h $(PREFIX)/include/graphserver
	cp dirfibheap.h $(PREFIX)/include/graphserver
	cp graph.h $(PREFIX)/include/graphserver
	cp hashtable_gs.h $(PREFIX)/include/graphserver
	cp hashtable_itr.h $(PREFIX)/include/graphserver
	cp edgetypes.h $(PREFIX)/include/graphserver
	cp hashtable.h $(PREFIX)/include/graphserver
	cp hashtable_utility.h $(PREFIX)/include/graphserver
	cp hashtable_private.h $(PREFIX)/include/graphserver
	cp statetypes.h $(PREFIX)/include/graphserver

clean:
	rm -f *.o *.so *~ *.d
