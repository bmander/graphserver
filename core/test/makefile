
SRCS = testsetparent.c deadend.c hops.c streetprofile.c testdestroystates.c test_crossing.c
TESTS = $(SRCS:.c=)

all: $(TESTS)

clean:
	rm $(TESTS)	

%: %.c ../libgraphserver.so
	cc -g $< ../libgraphserver.so -o $@ -lm 
