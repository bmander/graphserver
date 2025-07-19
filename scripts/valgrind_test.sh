#!/bin/bash

# Valgrind Memory Leak Detection Script for Graphserver
# This script runs all tests under Valgrind to detect memory leaks and errors

set -e

echo "Graphserver Valgrind Memory Analysis"
echo "===================================="

# Check if Valgrind is available
if ! command -v valgrind &> /dev/null; then
    echo "Error: Valgrind is not installed"
    echo "Install with: sudo apt-get install valgrind"
    exit 1
fi

# Build directory
BUILD_DIR="/workspaces/graphserver/core/build"

if [ ! -d "$BUILD_DIR" ]; then
    echo "Error: Build directory not found. Please run 'make' first."
    exit 1
fi

cd "$BUILD_DIR"

# Valgrind options
VALGRIND_OPTS="--tool=memcheck --leak-check=full --show-leak-kinds=all --track-origins=yes --verbose --error-exitcode=1"

# Test executables to check
TESTS=(
    "test_vertex"
    "test_edge"
    "test_memory"
    "test_engine"
    "test_planner"
    "test_integration"
)

echo "Running Valgrind analysis on all test executables..."
echo ""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

for test in "${TESTS[@]}"; do
    if [ ! -f "$test" ]; then
        echo "Warning: Test executable '$test' not found, skipping..."
        continue
    fi
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo "Analyzing $test..."
    echo "----------------------------------------"
    
    # Create output file for this test
    OUTPUT_FILE="valgrind_${test}.log"
    
    # Run Valgrind
    if valgrind $VALGRIND_OPTS ./$test &> "$OUTPUT_FILE"; then
        echo "✓ $test: PASS (no memory errors detected)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        # Check for any leaks in the output
        if grep -q "All heap blocks were freed -- no leaks are possible" "$OUTPUT_FILE"; then
            echo "  ✓ No memory leaks detected"
        elif grep -q "definitely lost: 0 bytes" "$OUTPUT_FILE" && grep -q "possibly lost: 0 bytes" "$OUTPUT_FILE"; then
            echo "  ✓ No definite memory leaks detected"
        else
            echo "  ⚠ Memory leaks may be present (check $OUTPUT_FILE)"
        fi
    else
        echo "✗ $test: FAIL (memory errors detected)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        
        # Show summary of errors
        echo "  Error summary:"
        grep -E "(ERROR SUMMARY|definitely lost|possibly lost|still reachable)" "$OUTPUT_FILE" | head -5
        echo "  Full details in: $OUTPUT_FILE"
    fi
    
    echo ""
done

echo "========================================"
echo "Valgrind Analysis Summary"
echo "========================================"
echo "Total tests analyzed: $TOTAL_TESTS"
echo "Passed (no errors): $PASSED_TESTS"
echo "Failed (errors found): $FAILED_TESTS"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed Valgrind analysis!"
    echo "No memory leaks or errors detected."
    exit 0
else
    echo ""
    echo "❌ Some tests failed Valgrind analysis."
    echo "Check the individual log files for details:"
    ls -la valgrind_*.log
    exit 1
fi