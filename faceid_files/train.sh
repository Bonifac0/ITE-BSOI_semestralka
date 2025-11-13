#!/bin/bash
#should be run from where .git is (git base dir)(eg. /workplace/repo)

set -o nounset
set -o errexit
set -o pipefail

if [[ -f ".venv/bin/python3" ]]; then
    echo "Training Face ID model..."
    ./.venv/bin/python3 src/faceid/train_model.py
else
    echo "It seems like you are training the model on VM. Its ok, but next push will erase this training."
    read -p "Do you want to continue? (y/n): " choice
    case "$choice" in
        [Yy]* )
            echo "Running example.py..."
            ./../venv/bin/python3 src/faceid/train_model.py
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
