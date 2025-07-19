#include "../include/gs_memory.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdint.h>

// Memory block structure for chained blocks
typedef struct MemoryBlock {
    struct MemoryBlock* next;
    size_t size;
    size_t used;
    uint8_t* data;
} MemoryBlock;

// Arena structure
struct GraphserverArena {
    MemoryBlock* first_block;
    MemoryBlock* current_block;
    size_t default_block_size;
    GraphserverMemoryStats stats;
};

// Utility function to align size
static size_t align_size(size_t size, size_t alignment) {
    return (size + alignment - 1) & ~(alignment - 1);
}

// Utility function to align pointer
static void* align_pointer(void* ptr, size_t alignment) {
    uintptr_t addr = (uintptr_t)ptr;
    uintptr_t aligned = (addr + alignment - 1) & ~(alignment - 1);
    return (void*)aligned;
}

// Create a new memory block
static MemoryBlock* create_memory_block(size_t size) {
    // Ensure minimum size
    if (size < GS_MIN_ARENA_SIZE) {
        size = GS_MIN_ARENA_SIZE;
    }
    
    // Allocate the block structure and data together for cache efficiency
    size_t total_size = sizeof(MemoryBlock) + size;
    MemoryBlock* block = malloc(total_size);
    if (!block) return NULL;
    
    block->next = NULL;
    block->size = size;
    block->used = 0;
    block->data = (uint8_t*)(block + 1); // Data immediately follows the header
    
    return block;
}

// Destroy a chain of memory blocks
static void destroy_memory_blocks(MemoryBlock* block) {
    while (block) {
        MemoryBlock* next = block->next;
        free(block);
        block = next;
    }
}

// Find or create a block with enough space
static MemoryBlock* find_block_with_space(GraphserverArena* arena, size_t size) {
    // Try current block first
    if (arena->current_block && 
        arena->current_block->size - arena->current_block->used >= size) {
        return arena->current_block;
    }
    
    // Search existing blocks
    MemoryBlock* block = arena->first_block;
    while (block) {
        if (block->size - block->used >= size) {
            arena->current_block = block;
            return block;
        }
        block = block->next;
    }
    
    // Need a new block
    size_t new_block_size = arena->default_block_size;
    if (size > new_block_size) {
        new_block_size = align_size(size, GS_MEMORY_ALIGNMENT);
    }
    
    MemoryBlock* new_block = create_memory_block(new_block_size);
    if (!new_block) return NULL;
    
    // Add to the chain
    if (!arena->first_block) {
        arena->first_block = new_block;
    } else {
        // Find the last block and append
        block = arena->first_block;
        while (block->next) {
            block = block->next;
        }
        block->next = new_block;
    }
    
    arena->current_block = new_block;
    arena->stats.num_blocks++;
    
    return new_block;
}

// Arena implementation
GraphserverArena* gs_arena_create(size_t initial_size) {
    if (initial_size == 0) {
        initial_size = GS_DEFAULT_ARENA_SIZE;
    }
    
    GraphserverArena* arena = malloc(sizeof(GraphserverArena));
    if (!arena) return NULL;
    
    arena->default_block_size = initial_size;
    arena->first_block = NULL;
    arena->current_block = NULL;
    
    // Initialize stats
    memset(&arena->stats, 0, sizeof(GraphserverMemoryStats));
    
    // Create the first block
    arena->first_block = create_memory_block(initial_size);
    if (!arena->first_block) {
        free(arena);
        return NULL;
    }
    
    arena->current_block = arena->first_block;
    arena->stats.num_blocks = 1;
    
    return arena;
}

void* gs_arena_alloc(GraphserverArena* arena, size_t size) {
    return gs_arena_alloc_aligned(arena, size, GS_MEMORY_ALIGNMENT);
}

void* gs_arena_alloc_aligned(GraphserverArena* arena, size_t size, size_t alignment) {
    if (!arena || size == 0) return NULL;
    
    // Ensure alignment is a power of 2
    if (alignment == 0 || (alignment & (alignment - 1)) != 0) {
        alignment = GS_MEMORY_ALIGNMENT;
    }
    
    // Align the size
    size_t aligned_size = align_size(size, alignment);
    
    // Find a block with enough space
    MemoryBlock* block = find_block_with_space(arena, aligned_size + alignment - 1);
    if (!block) return NULL;
    
    // Calculate the aligned pointer within the block
    uint8_t* raw_ptr = block->data + block->used;
    void* aligned_ptr = align_pointer(raw_ptr, alignment);
    
    // Calculate how much space we actually need
    size_t space_needed = (uint8_t*)aligned_ptr - raw_ptr + size;
    
    // Make sure we still have enough space after alignment
    if (block->size - block->used < space_needed) {
        // This shouldn't happen if find_block_with_space worked correctly
        return NULL;
    }
    
    // Update block usage
    block->used += space_needed;
    
    // Update stats
    arena->stats.total_allocated += space_needed;
    arena->stats.total_requested += size;
    arena->stats.num_allocations++;
    
    // Update peak usage
    size_t current_usage = gs_arena_get_usage(arena);
    if (current_usage > arena->stats.peak_usage) {
        arena->stats.peak_usage = current_usage;
    }
    
    return aligned_ptr;
}

void* gs_arena_calloc(GraphserverArena* arena, size_t count, size_t size) {
    if (count == 0 || size == 0) return NULL;
    
    // Check for overflow
    size_t total_size = count * size;
    if (total_size / count != size) return NULL;
    
    void* ptr = gs_arena_alloc(arena, total_size);
    if (ptr) {
        memset(ptr, 0, total_size);
    }
    
    return ptr;
}

void gs_arena_reset(GraphserverArena* arena) {
    if (!arena) return;
    
    // Reset usage for all blocks
    MemoryBlock* block = arena->first_block;
    while (block) {
        block->used = 0;
        block = block->next;
    }
    
    // Reset current block to first
    arena->current_block = arena->first_block;
    
    // Update stats
    arena->stats.num_resets++;
    // Don't reset counters, keep them for total statistics
}

GraphserverResult gs_arena_get_stats(const GraphserverArena* arena, GraphserverMemoryStats* out_stats) {
    if (!arena || !out_stats) return GS_ERROR_NULL_POINTER;
    
    *out_stats = arena->stats;
    return GS_SUCCESS;
}

size_t gs_arena_get_usage(const GraphserverArena* arena) {
    if (!arena) return 0;
    
    size_t total_used = 0;
    MemoryBlock* block = arena->first_block;
    while (block) {
        total_used += block->used;
        block = block->next;
    }
    
    return total_used;
}

bool gs_arena_can_alloc(const GraphserverArena* arena, size_t size) {
    if (!arena || size == 0) return false;
    
    size_t aligned_size = align_size(size, GS_MEMORY_ALIGNMENT);
    
    // Check current block first
    if (arena->current_block && 
        arena->current_block->size - arena->current_block->used >= aligned_size) {
        return true;
    }
    
    // Check other existing blocks
    MemoryBlock* block = arena->first_block;
    while (block) {
        if (block->size - block->used >= aligned_size) {
            return true;
        }
        block = block->next;
    }
    
    // We would need a new block - this is always possible (assuming system memory)
    // but we can't guarantee it without actually trying
    return true;
}

void gs_arena_destroy(GraphserverArena* arena) {
    if (!arena) return;
    
    destroy_memory_blocks(arena->first_block);
    free(arena);
}