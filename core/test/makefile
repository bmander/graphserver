
SRCS = testsetparent.c deadend.c hops.c streetprofile.c testdestroystates.c test_crossing.c init_prio_queue.c contract.c testheap.c test_ch.c
TESTS = $(SRCS:.c=)

all: $(TESTS)

clean:
	rm $(TESTS)	

%: %.c ../libgraphserver.so
	cc -g $< ../libgraphserver.so -o $@ -lm 
