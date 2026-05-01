#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Downloading Spacy NLP model..."
python -m spacy download en_core_web_md

echo "Build complete!"
