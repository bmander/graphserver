
SRCS = testsetparent.c streetprofile.c testdestroystates.c thsprofile.c test_batch_create.c deadend.c
TESTS = $(SRCS:.c=)

all: $(TESTS)

clean:
	rm $(TESTS)	

%: %.c ../core/libgraphserver.so
	cc -g $< ../core/libgraphserver.so -o $@ -lm -liberty
