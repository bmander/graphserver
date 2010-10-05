all: libgraphserver.so

# to override base installation directory run
# PREFIX=... make install
PREFIX=/usr

OBJECTS= fibheap/dirfibheap.o \
	fibheap/fibheap.o \
	graph.o \
	hashtable/hashtable.o \
	hashtable/hashtable_gs.o \
	hashtable/hashtable_itr.o \
	hashtable/hashtable_utility.o \
    state.o \
    walkoptions.o \
    edgetypes/elapsehelpers.o \
    edgetypes/link.o \
    edgetypes/street.o \
    edgetypes/egress.o \
    edgetypes/wait.o \
    edgetypes/elapsetime.o \
    edgetypes/headway.o \
    edgetypes/tripboard.o \
    edgetypes/headwayboard.o \
    edgetypes/headwayalight.o \
    edgetypes/crossing.o \
    edgetypes/tripalight.o \
    edgetypes/custompayload.o \
    edgetypes/combination.o \
    edgepayload.o \
    list.o \
    servicecalendar.o \
    timezone.o \
    path.o \
    vector.o \
    contraction.o \
    heap.o

# You know what? Honestly? I don't know what most of these switches do.
CFLAGS=-g -fno-strict-aliasing -O2 -fPIC -Wall
LDFLAGS= -L. -Bsymbolic-functions -Wall -ldl -lm -lc

OS := $(shell uname)

ifeq ($(OS),Darwin)
  LDFLAGS += -dynamiclib
else
  LDFLAGS += -shared
endif

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
	cp fibheap/fibheap.h $(PREFIX)/include/graphserver
	cp fibheap/dirfibheap.h $(PREFIX)/include/graphserver
	cp graph.h $(PREFIX)/include/graphserver
	cp hashtable/hashtable_gs.h $(PREFIX)/include/graphserver
	cp hashtable/hashtable_itr.h $(PREFIX)/include/graphserver
	cp hashtable/hashtable.h $(PREFIX)/include/graphserver
	cp hashtable/hashtable_utility.h $(PREFIX)/include/graphserver
	cp hashtable/hashtable_private.h $(PREFIX)/include/graphserver

clean:
	rm -f *.{o,so,~,d} */*.{o,so,~,d} 
