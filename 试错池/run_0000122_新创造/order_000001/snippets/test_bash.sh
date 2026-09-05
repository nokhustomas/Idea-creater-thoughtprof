#!/bin/bash
# Backup script
backup() {
    cp "$1" "${1}.bak"
    echo "Done"
}
