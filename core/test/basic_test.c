#include <stdio.h>
#include <stdlib.h>
#include "../graphserver.h"

int main() {
    printf("Testing basic graphserver functionality...\n");
    
    // Test basic graph creation
    Graph* g = gNew();
    if (g == NULL) {
        printf("FAILED: Could not create graph\n");
        return 1;
    }
    printf("SUCCESS: Graph created\n");
    
    // Test basic vertex creation
    Vertex* v1 = gAddVertex(g, "vertex1");
    Vertex* v2 = gAddVertex(g, "vertex2");
    if (v1 == NULL || v2 == NULL) {
        printf("FAILED: Could not create vertices\n");
        gDestroy(g);
        return 1;
    }
    printf("SUCCESS: Vertices created\n");
    
    // Clean up
    gDestroy(g);
    printf("SUCCESS: All basic tests passed!\n");
    
    return 0;
}