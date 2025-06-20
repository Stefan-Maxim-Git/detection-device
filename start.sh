#!/bin/bash

set -e

if ! pgrep -f "ollama serve" > /dev/null/; then
    echo "Starting Ollama server..."
    nohup ollama serve > ollama_server.log 2>&1 &
    sleep 2
else
    echo "Ollama server already running!"
fi

MODEL="gemma:2b-instruct"
if ! ollama list | grep -q "$MODEL"; then
    echo "Pulling Ollama model..."
    ollama pull "$MODEL"
else
    echo "Ollama model already present."
fi

echo "Checking with Ollama API..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "Ollama API responded succesfully!"
        break
    fi
    sleep 1
done

echo "Sourcing venv for main app..."
source setup_env.sh

if ! pgrep -f "info_server.py" > /dev/null; then
    echo "Starting SLM/TTS server..."
    nohup python src/info_server.py > slm_tts.log 2>&1 &
    sleep 1
else
    echo "SLM/TTS server already running!"
fi

echo "Starting main app..."
LIBCAMERA_LOG_LEVELS="*:2" python main.py


