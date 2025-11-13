#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

if [[ -f "src/faceid/train_model.py" ]]; then
    echo "Training Face ID model..."
    ./.venv/bin/python3 src/faceid/train_model.py
else
    echo "It seems like you are training the model on WM. Its ok, but next push will erase this training."
    read -p "Do you want to continue? (y/n): " choice
    case "$choice" in
        [Yy]* )
            echo "Running example.py..."
            ./.venv/bin/python3 src/example.py
            ;;
        [Nn]* )
            echo "Aborting."
            exit 1
            ;;
        * )
            echo "Invalid response. Aborting."
            exit 1
            ;;
    esac
fi
