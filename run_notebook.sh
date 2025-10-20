#!/bin/bash

# Script to activate virtual environment and run Jupyter notebook
# Usage: ./run_notebook.sh

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting Jupyter notebook server..."
echo "The notebook will open in your default browser."
echo "To stop the server, press Ctrl+C in this terminal."
echo ""

jupyter notebook
