#!/bin/bash
# AI Memory Assistant - Quality Assurance Runner
# Air-gapped compatible - runs all quality tools locally

set -e  # Exit on any error

echo "🤖 AI Memory Assistant - Quality Assurance Suite"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory (look for multiple key indicators)
if [ ! -f "scripts/analytics_dashboard.py" ] || [ ! -d "services" ] || [ ! -d "frontend" ]; then
    print_error "Please run this script from the project root directory"
    print_error "Expected structure: scripts/, services/, frontend/ directories"
    exit 1
fi

# Function to run tests
run_tests() {
    print_status "Running comprehensive test suite..."
    # TODO: Update to use actual test file location or pytest
    if [ -f "services/integration/test_suite.py" ]; then
        if python3 services/integration/test_suite.py; then
            print_success "All tests passed!"
            return 0
        else
            print_error "Some tests failed!"
            return 1
        fi
    else
        print_warning "Test suite not found at services/integration/test_suite.py - running pytest instead"
        if pytest -v; then
            print_success "Pytest tests passed!"
            return 0
        else
            print_error "Pytest tests failed!"
            return 1
        fi
    fi
}

# Function to run analytics
run_analytics() {
    print_status "Generating analytics report..."
    if python3 scripts/analytics_dashboard.py; then
        print_success "Analytics report generated!"
        return 0
    else
        print_error "Analytics generation failed!"
        return 1
    fi
}

# Function to generate documentation
generate_docs() {
    print_status "Generating documentation..."
    if [ -f "scripts/generate_docs.py" ]; then
        if python3 scripts/generate_docs.py; then
            print_success "Documentation generated!"
            return 0
        else
            print_error "Documentation generation failed!"
            return 1
        fi
    else
        print_warning "Documentation generator not found at scripts/generate_docs.py - skipping"
        return 0
    fi
}

# Function to run local CI/CD
run_ci() {
    print_status "Running local CI/CD pipeline..."
    if [ -f "scripts/local_ci.sh" ]; then
        if ./scripts/local_ci.sh; then
            print_success "CI/CD pipeline completed!"
            return 0
        else
            print_error "CI/CD pipeline failed!"
            return 1
        fi
    else
        print_warning "Local CI script not found at scripts/local_ci.sh - skipping"
        return 0
    fi
}

# Function to check system health
check_health() {
    print_status "Checking system health..."

    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker services are running"
    else
        print_warning "Docker services may not be running"
    fi

    # Check database connectivity
    if python3 -c "
import sys
import os
sys.path.insert(0, 'services')

# Set up test environment
os.environ['AI_BRAIN_DB_URL'] = 'sqlite:///:memory:'

from ai_brain.db import init_db, get_session
from sqlalchemy import text

try:
    # Initialize database
    init_db()
    
    # Test connection
    session = get_session()
    result = session.exec(text('SELECT 1')).first()
    print('Database connection: OK')
    print('Test query result:', result)
except Exception as e:
    print(f'Database connection: FAILED - {e}')
    import sys
    sys.exit(1)
"; then
        print_success "Database connectivity OK"
    else
        print_error "Database connectivity issues!"
        return 1
    fi

    return 0
}

# Main execution
main() {
    local start_time=$(date +%s)
    local failed_steps=()

    echo "Starting Quality Assurance Suite..."
    echo ""

    # Run health check first
    if ! check_health; then
        failed_steps+=("health_check")
        print_warning "Health check failed, but continuing with other checks..."
    fi

    # Run tests
    if ! run_tests; then
        failed_steps+=("tests")
    fi

    # Generate analytics
    if ! run_analytics; then
        failed_steps+=("analytics")
    fi

    # Generate documentation
    if ! generate_docs; then
        failed_steps+=("documentation")
    fi

    # Run CI/CD (optional, as it might be more comprehensive)
    if [ -f "scripts/local_ci.sh" ]; then
        if ! run_ci; then
            failed_steps+=("ci_cd")
        fi
    else
        print_warning "Local CI/CD script not found, skipping..."
    fi

    # Calculate runtime
    local end_time=$(date +%s)
    local runtime=$((end_time - start_time))

    echo ""
    echo "=================================================="
    echo "Quality Assurance Suite Complete"
    echo "Runtime: ${runtime} seconds"

    if [ ${#failed_steps[@]} -eq 0 ]; then
        print_success "All quality checks passed! 🎉"
        echo ""
        echo "Generated files:"
        echo "  - analytics_report.json"
        echo "  - analytics_report.md"
        echo "  - docs/ (documentation directory)"
        echo "  - test_results/ (if tests generated output)"
        exit 0
    else
        print_error "Some quality checks failed: ${failed_steps[*]}"
        echo ""
        echo "Please review the errors above and fix any issues."
        exit 1
    fi
}

# Check command line arguments
case "${1:-all}" in
    "test"|"tests")
        run_tests
        ;;
    "analytics")
        run_analytics
        ;;
    "docs"|"documentation")
        generate_docs
        ;;
    "ci")
        run_ci
        ;;
    "health")
        check_health
        ;;
    "all")
        main
        ;;
    *)
        echo "Usage: $0 [test|analytics|docs|ci|health|all]"
        echo "  test        - Run test suite"
        echo "  analytics   - Generate analytics report"
        echo "  docs        - Generate documentation"
        echo "  ci          - Run local CI/CD pipeline"
        echo "  health      - Check system health"
        echo "  all         - Run all quality checks (default)"
        exit 1
        ;;
esac