#ifndef GS_STRING_DICT_H
#define GS_STRING_DICT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file gs_string_dict.h
 * @brief String dictionary for mapping strings to unsigned 16-bit integers
 * 
 * This module provides a thread-safe string dictionary that maps strings to
 * unique unsigned 16-bit integer IDs. The dictionary is designed for scenarios
 * where the same strings are used repeatedly (like metadata keys) and memory
 * optimization is important.
 * 
 * Key features:
 * - Thread-safe operations using read-write locks
 * - String interning to avoid duplication
 * - Support for up to 65,535 unique strings (ID 0 reserved for invalid)
 * - Bulk registration operations for efficiency
 */

/**
 * @defgroup string_dict String Dictionary
 * @{
 */

// Reserved ID for invalid/null keys
#define GS_INVALID_KEY_ID 0

/**
 * Initialize the global string dictionary.
 * This must be called before any other dictionary operations.
 * Thread-safe: Yes (but should only be called once at program startup)
 */
void gs_string_dict_init(void);

/**
 * Clean up the global string dictionary and free all resources.
 * This should be called once at program shutdown.
 * Thread-safe: Yes (but should only be called once at program shutdown)
 */
void gs_string_dict_cleanup(void);

/**
 * Register a string in the dictionary and get its unique ID.
 * If the string is already registered, returns the existing ID.
 * 
 * @param str The string to register (must not be NULL)
 * @return Unique ID for the string, or GS_INVALID_KEY_ID on error
 * 
 * Thread-safe: Yes (uses write lock if new string, read lock if existing)
 */
uint16_t gs_string_dict_register(const char* str);

/**
 * Get the string associated with a given ID.
 * 
 * @param id The ID to look up
 * @return Pointer to the string, or NULL if ID is invalid
 * 
 * Thread-safe: Yes (uses read lock)
 * 
 * Note: The returned pointer is valid until gs_string_dict_cleanup() is called.
 */
const char* gs_string_dict_get(uint16_t id);

/**
 * Register multiple strings at once for efficiency.
 * 
 * @param strings Array of strings to register (must not be NULL)
 * @param ids Array to store the resulting IDs (must not be NULL)
 * @param count Number of strings to register
 * 
 * Thread-safe: Yes (uses write lock for the entire operation)
 * 
 * Note: If any string is NULL, the corresponding ID will be GS_INVALID_KEY_ID
 */
void gs_string_dict_register_batch(const char** strings, uint16_t* ids, size_t count);

/**
 * Check if a string is already registered in the dictionary.
 * 
 * @param str The string to check (must not be NULL)
 * @return true if the string is registered, false otherwise
 * 
 * Thread-safe: Yes (uses read lock)
 */
bool gs_string_dict_contains(const char* str);

/**
 * Get the current number of strings in the dictionary.
 * 
 * @return Number of registered strings
 * 
 * Thread-safe: Yes (uses read lock)
 */
size_t gs_string_dict_size(void);

/**
 * Check if the dictionary has been initialized.
 * 
 * @return true if initialized, false otherwise
 * 
 * Thread-safe: Yes (simple atomic read)
 */
bool gs_string_dict_is_initialized(void);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_STRING_DICT_H