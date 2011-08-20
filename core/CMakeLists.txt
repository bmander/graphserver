cmake_minimum_required( VERSION 2.6 )
project( graphserver )
add_library( graphserver SHARED 
             contraction.c
             contraction.h
             edgepayload.c
             edgepayload.h
             graph.c
             graph.h
             graphserver.h
             heap.c
             heap.h
             list.c
             list.h
             path.c
             path.h
             router.c
             servicecalendar.c
             servicecalendar.h
             state.c
             state.h
             timezone.c
             timezone.h
             vector.c
             vector.h
             walkoptions.c
             walkoptions.h )
