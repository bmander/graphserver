cmake_minimum_required( VERSION 2.6 )
project( graphserver )
add_library( graphserver SHARED 
             edgepayload.c
             graph.c
             heap.c
             list.c
             path.c
             servicecalendar.c
             state.c
             timezone.c
             vector.c
             walkoptions.c
             edgetypes/crossing.c
             edgetypes/custompayload.c
             edgetypes/egress.c
             edgetypes/elapsehelpers.c
             edgetypes/elapsetime.c
             edgetypes/headwayalight.c
             edgetypes/headwayboard.c
             edgetypes/headway.c
             edgetypes/link.c
             edgetypes/street.c
             edgetypes/tripalight.c
             edgetypes/tripboard.c
             edgetypes/wait.c
             fibheap/fibheap.c
             hashtable/hashtable.c
             hashtable/hashtable_gs.c
             hashtable/hashtable_itr.c
             hashtable/hashtable_utility.c )
