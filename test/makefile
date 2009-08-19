
SRCS = shortcut.c init_prio_queue.c combination.c contract.c testheap.c
TESTS = $(SRCS:.c=)

all: $(TESTS)

clean:
	rm $(TESTS)	

%: %.c ../core/libgraphserver.so
	cc -pg -g $< ../core/*.o -o $@ -lm -liberty