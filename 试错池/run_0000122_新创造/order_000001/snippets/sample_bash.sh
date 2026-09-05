#!/bin/bash
# Bash snippet: File backup
backup_file() {
    cp "$1" "${1}.bak.$(date +%s)"
    echo "Backed up $1"
}
