
SRCS = shortcut.c init_prio_queue.c combination.c contract.c
TESTS = $(SRCS:.c=)

all: $(TESTS)

clean:
	rm $(TESTS)	

%: %.c ../core/libgraphserver.so
	cc -g $< ../core/libgraphserver.so -o $@ -lm -liberty
