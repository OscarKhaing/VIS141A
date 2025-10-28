#!/bin/bash
#
# run.sh - Helper script to launch the music visualization wall
#
# Usage:
#   ./run.sh <audio_file>           # Run with audio file
#   ./run.sh <audio_file> --debug   # Run with debug HUD
#

# Configuration
NUM_PROCESSES=4
SCRIPT="wall.py"

# Check if audio file provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <audio_file> [--debug]"
    echo ""
    echo "Example:"
    echo "  $0 assets/track.wav"
    echo "  $0 assets/track.wav --debug"
    exit 1
fi

AUDIO_FILE="$1"
EXTRA_ARGS="${@:2}"

# Check if audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
    echo "ERROR: Audio file not found: $AUDIO_FILE"
    exit 1
fi

# Check if running on cluster or local
if [ -f "mach_file" ]; then
    echo "Running on cluster with machine file..."
    mpiexec -n $NUM_PROCESSES -pernode --machinefile mach_file \
        python3 $SCRIPT --audio "$AUDIO_FILE" $EXTRA_ARGS
else
    echo "Running locally..."
    mpiexec -n $NUM_PROCESSES \
        python3 $SCRIPT --audio "$AUDIO_FILE" $EXTRA_ARGS
fi
