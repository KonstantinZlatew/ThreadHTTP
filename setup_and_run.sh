#!/bin/bash
# Setup and Run Benchmark Suite
# Автоматизиран скрипт за подготовка и изпълнение на benchmark тестовете

set -e  # Exit on error

echo "=========================================="
echo "HTTP Server Benchmark Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check Python version
echo ""
echo "1. Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

# Check wrk installation
echo ""
echo "2. Checking wrk..."
if command -v wrk &> /dev/null; then
    print_success "wrk is installed"
else
    print_error "wrk not found"
    echo ""
    echo "To install wrk:"
    echo "  Ubuntu/Debian: sudo apt-get install wrk"
    echo "  macOS:         brew install wrk"
    echo "  From source:   https://github.com/wg/wrk"
    echo ""
    read -p "Do you want to try installing wrk? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Attempting to install wrk via apt-get..."
            sudo apt-get update && sudo apt-get install -y wrk
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "Attempting to install wrk via brew..."
            brew install wrk
        else
            print_error "Automatic installation not supported for this OS"
            exit 1
        fi
    else
        exit 1
    fi
fi

# Check/Install Python dependencies
echo ""
echo "3. Checking Python dependencies..."
if python3 -c "import matplotlib" 2>/dev/null; then
    print_success "matplotlib is installed"
else
    print_warning "matplotlib not found"
    echo "Installing matplotlib..."
    pip3 install matplotlib
    print_success "matplotlib installed"
fi

# Create necessary directories
echo ""
echo "4. Creating directories..."
mkdir -p results
mkdir -p wrk_scripts
print_success "Directories created"

# Check if server.py exists
echo ""
echo "5. Checking server files..."
if [ ! -f "server.py" ]; then
    print_error "server.py not found in current directory"
    exit 1
fi
print_success "server.py found"

if [ ! -f "benchmark_lib.py" ]; then
    print_error "benchmark_lib.py not found"
    exit 1
fi
print_success "benchmark_lib.py found"

if [ ! -f "run_benchmarks.py" ]; then
    print_error "run_benchmarks.py not found"
    exit 1
fi
print_success "run_benchmarks.py found"

if [ ! -f "analyze_results.py" ]; then
    print_error "analyze_results.py not found"
    exit 1
fi
print_success "analyze_results.py found"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start the server:       python3 server.py"
echo "  2. Run benchmarks:         python3 run_benchmarks.py"
echo "  3. Generate reports:       python3 analyze_results.py"
echo ""
echo "Or use this script with options:"
echo "  ./setup_and_run.sh --full    (runs everything)"
echo "  ./setup_and_run.sh --server  (starts server only)"
echo "  ./setup_and_run.sh --bench   (runs benchmarks only)"
echo ""

# Handle command line arguments
if [ "$1" == "--full" ]; then
    echo "=========================================="
    echo "Running Full Benchmark Suite"
    echo "=========================================="
    
    # Start server in background
    echo ""
    echo "Starting server..."
    python3 server.py &
    SERVER_PID=$!
    print_success "Server started (PID: $SERVER_PID)"
    
    # Wait for server to start
    echo "Waiting for server to initialize..."
    sleep 3
    
    # Check if server is responding
    if curl -s http://127.0.0.1:9090 > /dev/null 2>&1; then
        print_success "Server is responding"
    else
        print_error "Server not responding"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    # Run benchmarks
    echo ""
    echo "Starting benchmarks (this will take ~20 minutes)..."
    if python3 run_benchmarks.py; then
        print_success "Benchmarks completed"
        
        # Generate reports
        echo ""
        echo "Generating reports and graphs..."
        if python3 analyze_results.py; then
            print_success "Reports generated"
            
            echo ""
            echo "=========================================="
            echo "Benchmark Complete!"
            echo "=========================================="
            echo ""
            echo "Generated files:"
            echo "  - bench21.png, bench22.png, bench23.png, bench24.png, bench25.png"
            echo "  - bench21.txt, bench22.txt, bench23.txt, bench24.txt, bench25.txt"
            echo "  - bench.txt (final analysis)"
            echo ""
            echo "Read bench.txt for detailed analysis and recommendations"
        else
            print_error "Report generation failed"
        fi
    else
        print_error "Benchmarks failed"
    fi
    
    # Stop server
    echo ""
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null
    print_success "Server stopped"
    
elif [ "$1" == "--server" ]; then
    echo ""
    echo "Starting server on http://127.0.0.1:9090..."
    echo "Press Ctrl+C to stop"
    python3 server.py
    
elif [ "$1" == "--bench" ]; then
    echo ""
    echo "Running benchmarks..."
    echo "Make sure the server is running on http://127.0.0.1:9090"
    sleep 2
    
    if python3 run_benchmarks.py; then
        print_success "Benchmarks completed"
        echo ""
        echo "Now run: python3 analyze_results.py"
    else
        print_error "Benchmarks failed"
        exit 1
    fi
fi