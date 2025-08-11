#!/bin/bash

# GraphServer Routing Profiler Runner
# Convenience script for running performance profiling

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "========================================================"
    echo "  GraphServer Core Routing Algorithm Profiler"
    echo "========================================================"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [OPTION] [SCENARIOS]"
    echo ""
    echo "Options:"
    echo "  quick         Quick test with 5 scenarios (default)"
    echo "  standard      Standard test with 25 scenarios"
    echo "  intensive     Intensive test with 50 scenarios"  
    echo "  stress        Stress test with 100 scenarios"
    echo "  gprof         Run with gprof profiling (25 scenarios)"
    echo "  valgrind      Run with Valgrind memory profiling (10 scenarios)"
    echo "  compare       Performance comparison across scenario counts"
    echo "  build         Build profiler only (no execution)"
    echo "  clean         Clean build artifacts"
    echo "  help          Show this help message"
    echo ""
    echo "Custom scenarios:"
    echo "  $0 [NUMBER]   Run with specific number of scenarios (1-200)"
    echo ""
    echo "Examples:"
    echo "  $0                # Quick test (5 scenarios)"
    echo "  $0 standard       # Standard test (25 scenarios)"
    echo "  $0 intensive      # Intensive test (50 scenarios)"
    echo "  $0 30             # Custom test (30 scenarios)"
    echo "  $0 gprof          # gprof profiling"
    echo "  $0 compare        # Performance comparison"
}

check_dependencies() {
    # Check if make is available
    if ! command -v make &> /dev/null; then
        echo -e "${RED}❌ Error: 'make' command not found${NC}"
        echo "Please install build-essential: sudo apt-get install build-essential"
        exit 1
    fi

    # Check if gcc is available
    if ! command -v gcc &> /dev/null; then
        echo -e "${RED}❌ Error: 'gcc' compiler not found${NC}"
        echo "Please install gcc: sudo apt-get install build-essential"
        exit 1
    fi

    echo -e "${GREEN}✅ Dependencies check passed${NC}"
}

build_profiler() {
    echo -e "${YELLOW}🔨 Building profiler...${NC}"
    
    if ! make build-core > /dev/null 2>&1; then
        echo -e "${RED}❌ Failed to build core library${NC}"
        echo "Try running: cd ../core && mkdir build && cd build && cmake .. && make"
        exit 1
    fi

    if ! make > /dev/null 2>&1; then
        echo -e "${RED}❌ Failed to build profiler${NC}"
        echo "Check build output with: make"
        exit 1
    fi

    echo -e "${GREEN}✅ Profiler built successfully${NC}"
}

run_profiler() {
    local scenarios=$1
    local mode=$2
    
    echo -e "${BLUE}🚀 Running profiler with ${scenarios} scenarios...${NC}"
    echo ""
    
    case $mode in
        "gprof")
            make gprof SCENARIOS=$scenarios
            ;;
        "valgrind")
            if ! command -v valgrind &> /dev/null; then
                echo -e "${YELLOW}⚠️  Valgrind not found, installing...${NC}"
                sudo apt-get update && sudo apt-get install -y valgrind
            fi
            make valgrind SCENARIOS=$scenarios
            ;;
        *)
            ./profile_routing $scenarios
            ;;
    esac
}

run_comparison() {
    echo -e "${BLUE}⚖️  Running performance comparison...${NC}"
    echo ""
    
    echo -e "${YELLOW}Testing 5 scenarios:${NC}"
    time ./profile_routing 5 | tail -5
    
    echo ""
    echo -e "${YELLOW}Testing 15 scenarios:${NC}"
    time ./profile_routing 15 | tail -5
    
    echo ""
    echo -e "${YELLOW}Testing 25 scenarios:${NC}"
    time ./profile_routing 25 | tail -5
    
    echo ""
    echo -e "${GREEN}✅ Performance comparison completed${NC}"
}

main() {
    print_header
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Default values
    local mode="standard"
    local scenarios=5
    
    # Parse arguments
    case "${1:-quick}" in
        "help"|"-h"|"--help")
            print_usage
            exit 0
            ;;
        "clean")
            echo -e "${YELLOW}🧹 Cleaning build artifacts...${NC}"
            make clean
            echo -e "${GREEN}✅ Clean completed${NC}"
            exit 0
            ;;
        "build")
            check_dependencies
            build_profiler
            exit 0
            ;;
        "quick")
            scenarios=5
            ;;
        "standard")
            scenarios=25
            ;;
        "intensive")
            scenarios=50
            ;;
        "stress")
            scenarios=100
            ;;
        "gprof")
            mode="gprof"
            scenarios=25
            ;;
        "valgrind")
            mode="valgrind"
            scenarios=10
            ;;
        "compare")
            check_dependencies
            build_profiler
            run_comparison
            exit 0
            ;;
        [0-9]*)
            scenarios=$1
            if [ $scenarios -lt 1 ] || [ $scenarios -gt 200 ]; then
                echo -e "${RED}❌ Number of scenarios must be between 1 and 200${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo ""
            print_usage
            exit 1
            ;;
    esac
    
    # Run profiler
    check_dependencies
    build_profiler
    run_profiler $scenarios $mode
    
    echo ""
    echo -e "${GREEN}🎉 Profiling completed!${NC}"
    echo ""
    echo -e "${YELLOW}💡 Next steps:${NC}"
    echo "  • Review performance bottlenecks in the output above"
    echo "  • Run 'gprof' mode for detailed function analysis"
    echo "  • Use 'valgrind' mode for memory profiling"
    echo "  • Try 'compare' mode to see performance across different loads"
    echo ""
    echo -e "${BLUE}📖 Documentation: scripts/README.md${NC}"
}

# Run main function with all arguments
main "$@"