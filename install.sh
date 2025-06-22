#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Install Ollama if not already installed:
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    echo "Ollama installed succesfully!"
else
    echo "Ollama already installed."
fi

# Source environment variables and activate virtual environment
echo "Sourcing environment variables and activating virtual environment..."
source setup_env.sh

# Install additional system dependencies (if needed)
echo "Installing additional system dependencies..."
sudo apt install -y rapidjson-dev

# Initialize variables
PYHAILORT_WHL=""
PYTAPPAS_WHL=""
TAG="25.3.1"

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --pyhailort) PYHAILORT_WHL="$2"; shift ;;
        --pytappas) PYTAPPAS_WHL="$2"; shift ;;
        --test) INSTALL_TEST_REQUIREMENTS=true ;;
        --all) DOWNLOAD_RESOURCES_FLAG="--all" ;;
        --tag) TAG="$2"; shift ;;   # New parameter to specify tag
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Install specified Python wheels
if [[ -n "$PYHAILORT_WHL" ]]; then
    echo "Installing pyhailort wheel: $PYHAILORT_WHL"
    pip install "$PYHAILORT_WHL"
fi

if [[ -n "$PYTAPPAS_WHL" ]]; then
    echo "Installing pytappas wheel: $PYTAPPAS_WHL"
    pip install "$PYTAPPAS_WHL"
fi

# Install the required Python dependencies
echo "Installing required Python dependencies..."
pip install -r requirements.txt

echo "Installation completed successfully."