#!/bin/bash
# Setup script for the demo

set -e

echo "=== Amplifier Multi-Worker Demo Setup ==="
echo

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set"
    echo
    echo "Please set your Anthropic API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo
    echo "Or create a .env file with:"
    echo "  ANTHROPIC_API_KEY=your-key-here"
    exit 1
fi

# Check that amplifier-core exists
AMPLIFIER_CORE_PATH="../related-projects/amplifier-core"
if [ ! -d "$AMPLIFIER_CORE_PATH" ]; then
    echo "Error: amplifier-core not found at $AMPLIFIER_CORE_PATH"
    echo
    echo "Please ensure amplifier-core is checked out at:"
    echo "  $AMPLIFIER_CORE_PATH"
    exit 1
fi

# Create workspace
echo "Creating workspace directory..."
mkdir -p .demo-workspace

# Initialize issues database (if needed)
echo "Initializing issues database..."
# The issue tool will auto-initialize on first use

echo
echo "=== Setup Complete! ==="
echo
echo "To run the demo:"
echo "  python demo.py"
echo
echo "The demo will:"
echo "  1. Create a foreman session that creates 5 issues"
echo "  2. Launch 3 worker sessions (2 coding, 1 research)"
echo "  3. Workers will process issues in parallel"
echo "  4. Foreman will monitor and unblock issues"
echo
