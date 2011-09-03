
SRCS = testsetparent.c deadend.c hops.c streetprofile.c testdestroystates.c test_crossing.c testheap.c testrealloc.c testbasic.c
TESTS = $(SRCS:.c=)
BUILDDIR = build

all: buildbuild $(TESTS)

clean:
	rm $(TESTS)

buildbuild:
	mkdir -p $(BUILDDIR)

%: %.c ../libgraphserver.so
	cc -g $< ../libgraphserver.so -o $(BUILDDIR)/$@ -lm -lgraphserver -L..
