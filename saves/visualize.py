#!/usr/bin/env python3
"""
All-in-One Music Visualization Script
======================================

Automatically detects audio format (MP3/WAV), converts if needed, and launches
synchronized 4-screen (2x2 grid) MPI visualization with real-time audio analysis.

USAGE
-----
    Local (single machine):
        mpiexec -n 4 python3 visualize.py <audio_file> [options]

    Cluster (multiple machines):
        mpiexec -n 4 -pernode --machinefile mach_file python3 visualize.py <audio_file> [options]

EXAMPLES
--------
    Basic usage (WAV file):
        mpiexec -n 4 python3 visualize.py assets/sine_sweep.wav

    Auto-convert MP3:
        mpiexec -n 4 python3 visualize.py assets/lone_digger.mp3

    With debug HUD:
        mpiexec -n 4 python3 visualize.py song.mp3 --debug

    Keep converted files:
        mpiexec -n 4 python3 visualize.py song.mp3 --keep-converted

    Cluster deployment:
        mpiexec -n 4 -pernode --machinefile mach_file python3 visualize.py song.mp3

OPTIONS
-------
    --debug             Show debug HUD with frame info, FPS, beat detection
    --keep-converted    Keep temporary converted WAV files (don't auto-delete)

FEATURES
--------
    - Auto-detects MP3 vs WAV format (by extension and file header)
    - Converts MP3 to WAV (mono, 44.1kHz, 16-bit) automatically if needed
    - Validates WAV format (ensures mono 44.1kHz requirement)
    - Launches synchronized 4-screen MPI visualization (2x2 grid)
    - Real-time audio analysis: STFT, mel filterbank, beat detection
    - Beat-responsive visuals: color changes, height boosts, flash effects
    - 4 color palettes, 4 scene backgrounds (cycle on beats)
    - 30 FPS synchronized rendering across all ranks
    - Auto-cleanup of temporary converted files

REQUIREMENTS
------------
    - Python 3.9+
    - MPI implementation (OpenMPI or MPICH)
    - mpi4py, numpy, pygame (see requirements.txt)
    - 4 MPI processes (2x2 grid)
    - Display server (X11 for Linux/macOS)

AUDIO FORMATS
-------------
    Input:  MP3 (.mp3) or WAV (.wav)
    Output: Mono WAV, 44.1kHz, 16-bit PCM (if conversion needed)

    Note: For WAV files, must already be mono 44.1kHz.
          For MP3 files, auto-converts to correct format.

CONTROLS
--------
    ESC or Q        Quit visualization
    Ctrl+C          Force quit (all ranks)

CLUSTER DEPLOYMENT
------------------
    Create machine file (mach_file) with one hostname per line:
        host1
        host2
        host3
        host4

    Then run:
        mpiexec -n 4 -pernode --machinefile mach_file python3 visualize.py song.mp3

    The -pernode flag ensures one process per machine (for 4 physical screens).

TROUBLESHOOTING
---------------
    "This program requires 4 MPI processes"
        → Always use: mpiexec -n 4

    "cannot load MPI library"
        → Don't run directly with python3, use mpiexec

    "WAV must be mono" or "WAV must be 44100Hz"
        → Use MP3 instead (auto-converts), or convert manually:
          python3 convert_mp3_to_wav.py input.mp3

    Windows not appearing
        → Check DISPLAY environment: export DISPLAY=:0

    Low FPS / stuttering
        → Use Ethernet (not WiFi) for cluster
        → Lower TARGET_FPS in config.py
        → Use shorter audio files for testing

FILE STRUCTURE
--------------
    Required files in same directory (saves/):
        - visualize.py (this file)
        - config.py
        - audio.py
        - visuals.py

    Optional (for testing):
        - wall.py (original MPI visualizer)
        - convert_mp3_to_wav.py (manual converter)
        - generate_test_audio.py (test audio generator)

AUTHOR
------
    VIS 141A - Visual Arts with MPI
    Music-Driven Multi-Screen Visualization Wall (Part 1)
    Using MPI patterns from examples: oneball.py, images.py, bcast.py
"""

import os
import sys
import argparse
import tempfile
import wave
import pygame
import numpy as np
from mpi4py import MPI

# Import local modules
from config import *
from audio import AudioStream
from visuals import BarVisualizer, render_debug_hud


# ============================================================================
# Audio Format Detection and Conversion
# ============================================================================

def detect_audio_format(filepath):
    """
    Detect if audio file is MP3 or WAV.

    Args:
        filepath: Path to audio file

    Returns:
        'mp3', 'wav', or 'unknown'
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.mp3', '.m4a', '.aac']:
        return 'mp3'
    elif ext == '.wav':
        return 'wav'
    else:
        # Try to detect by reading file header
        try:
            with open(filepath, 'rb') as f:
                header = f.read(12)
                if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                    return 'wav'
                elif header[:3] == b'ID3' or header[:2] == b'\xff\xfb':
                    return 'mp3'
        except:
            pass

    return 'unknown'


def validate_wav_format(filepath):
    """
    Check if WAV file is mono, 44.1kHz.

    Args:
        filepath: Path to WAV file

    Returns:
        tuple (is_valid, message)
    """
    try:
        with wave.open(filepath, 'rb') as wf:
            n_channels = wf.getnchannels()
            framerate = wf.getframerate()

            if n_channels != 1:
                return False, f"WAV must be mono (got {n_channels} channels)"

            if framerate != SR:
                return False, f"WAV must be {SR}Hz (got {framerate}Hz)"

            return True, "WAV format valid"
    except Exception as e:
        return False, f"Error reading WAV: {e}"


def convert_mp3_to_wav(mp3_path, wav_path=None, rank=0):
    """
    Convert MP3 to mono WAV (44.1kHz, 16-bit).
    Only rank 0 performs the conversion.

    Args:
        mp3_path: Path to input MP3
        wav_path: Path to output WAV (None = auto temp file)
        rank: MPI rank (only rank 0 converts)

    Returns:
        Path to WAV file
    """
    if rank != 0:
        return wav_path  # Non-rank-0 processes just return the path

    # Generate temp file if not specified
    if wav_path is None:
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(mp3_path))[0]
        wav_path = os.path.join(temp_dir, f"{base_name}_converted.wav")

    print(f"[Rank 0] Converting {mp3_path} to WAV format...")

    try:
        # Initialize pygame mixer
        pygame.mixer.init(frequency=SR, size=-16, channels=1)

        # Load MP3
        sound = pygame.mixer.Sound(mp3_path)

        # Get raw audio data
        samples = pygame.sndarray.array(sound)

        # Convert to mono if stereo
        if len(samples.shape) == 2:
            samples = samples.mean(axis=1)

        # Convert to int16
        samples = samples.astype(np.int16)

        # Write WAV file
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(SR)     # 44.1kHz
            wf.writeframes(samples.tobytes())

        pygame.quit()

        # Verify
        duration = len(samples) / SR
        print(f"[Rank 0] ✓ Converted to: {wav_path}")
        print(f"[Rank 0]   Duration: {duration:.1f}s ({int(duration//60)}m {int(duration%60)}s)")
        print(f"[Rank 0]   Format: Mono, {SR}Hz, 16-bit")

        return wav_path

    except Exception as e:
        print(f"[Rank 0] ERROR: Conversion failed: {e}")
        raise


def prepare_audio_file(input_path, keep_converted=False, rank=0):
    """
    Prepare audio file for visualization.
    Auto-detects format and converts if needed.

    Args:
        input_path: Path to input audio file
        keep_converted: If True, don't delete converted WAV files
        rank: MPI rank

    Returns:
        tuple (wav_path, is_temporary)
    """
    if rank == 0:
        print(f"[Rank 0] Preparing audio file: {input_path}")

    # Check if file exists
    if not os.path.exists(input_path):
        if rank == 0:
            print(f"[Rank 0] ERROR: File not found: {input_path}")
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    # Detect format
    file_format = detect_audio_format(input_path)

    if rank == 0:
        print(f"[Rank 0] Detected format: {file_format.upper()}")

    if file_format == 'wav':
        # Validate WAV format
        is_valid, message = validate_wav_format(input_path)

        if rank == 0:
            print(f"[Rank 0] {message}")

        if is_valid:
            return input_path, False  # Use original file, not temporary
        else:
            if rank == 0:
                print(f"[Rank 0] ERROR: {message}")
            raise ValueError(message)

    elif file_format == 'mp3':
        # Convert MP3 to WAV (only rank 0 does the conversion)
        wav_path = convert_mp3_to_wav(input_path, rank=rank)
        return wav_path, not keep_converted  # Temporary if not keeping

    else:
        if rank == 0:
            print(f"[Rank 0] ERROR: Unsupported audio format")
        raise ValueError(f"Unsupported audio format. Please provide MP3 or WAV file.")


# ============================================================================
# MPI Visualization Setup
# ============================================================================

def setup_pygame_window(rank):
    """
    Initialize pygame and create window for this rank.

    Args:
        rank: MPI rank (0-3)

    Returns:
        tuple (screen, clock) - pygame Surface and Clock
    """
    # Set display
    os.environ['DISPLAY'] = ':0.0'

    # Set window position based on rank
    pos = WINDOW_POSITIONS[rank]
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos[0]},{pos[1]}"

    # Initialize pygame
    pygame.display.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)

    # Create window
    screen = pygame.display.set_mode(
        (WIN_W, WIN_H),
        pygame.NOFRAME  # Borderless
    )
    pygame.display.set_caption(f"Music Visualization - Rank {rank}")

    # Create clock
    clock = pygame.time.Clock()

    return screen, clock


# ============================================================================
# Main Visualization Loop
# ============================================================================

def run_visualization(wav_path, debug=False, rank=0, comm=None):
    """
    Run the main MPI visualization loop.

    Args:
        wav_path: Path to WAV file
        debug: Show debug HUD
        rank: MPI rank
        comm: MPI communicator
    """
    # Setup pygame window
    screen, clock = setup_pygame_window(rank)

    # Initialize visualizer
    visualizer = BarVisualizer(rank, WIN_W, WIN_H)

    # Font for debug HUD
    debug_font = pygame.font.SysFont('monospace', 12) if debug else None

    # Rank 0: Initialize audio stream
    audio_stream = None
    if rank == 0:
        print(f"[Rank 0] Loading audio: {wav_path}")
        try:
            audio_stream = AudioStream(wav_path)
            duration = audio_stream.total_samples / SR
            print(f"[Rank 0] Audio loaded: {audio_stream.total_samples:,} samples "
                  f"({duration:.1f}s / {int(duration//60)}m {int(duration%60)}s)")
        except Exception as e:
            print(f"[Rank 0] ERROR loading audio: {e}")
            comm.Abort(1)

    # Synchronize before starting
    comm.Barrier()
    if rank == 0:
        print("[Rank 0] Starting visualization...")
        print("[Rank 0] Press ESC or Q to quit")

    # Main loop
    running = True
    frame_count = 0
    frame_data = None

    try:
        while running:
            # ================================================================
            # BARRIER: Synchronize all ranks at frame boundary
            # ================================================================
            comm.Barrier()

            # ================================================================
            # RANK 0: Read audio and broadcast frame data
            # ================================================================
            if rank == 0:
                # Get next audio analysis frame
                frame_data = audio_stream.get_next_frame()

                # Check for end of stream
                if frame_data['eos']:
                    print("[Rank 0] End of audio stream reached")
                    running = False

                # Broadcast frame data
                frame_data = comm.bcast(frame_data, root=0)
            else:
                # Other ranks: Receive frame data
                frame_data = comm.bcast(None, root=0)

            # Check if we should stop
            if frame_data and frame_data.get('eos', False):
                running = False
                break

            # ================================================================
            # ALL RANKS: Render visualization
            # ================================================================
            visualizer.render(screen, frame_data)

            # Render debug HUD if enabled
            if debug:
                render_debug_hud(screen, frame_data, rank, debug_font)

            # Update display
            pygame.display.update()

            # ================================================================
            # EVENT HANDLING: Check for quit
            # ================================================================
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False

            # ================================================================
            # FRAME RATE CONTROL
            # ================================================================
            clock.tick(TARGET_FPS)
            frame_count += 1

            # Print FPS stats periodically
            if rank == 0 and frame_count % 100 == 0:
                actual_fps = clock.get_fps()
                print(f"[Rank 0] Frame {frame_count}, FPS: {actual_fps:.1f}, "
                      f"Time: {frame_data.get('t_sec', 0):.1f}s")

    except KeyboardInterrupt:
        if rank == 0:
            print("\n[Rank 0] Interrupted by user")
        running = False

    finally:
        # Cleanup
        comm.Barrier()

        if rank == 0:
            print(f"[Rank 0] Visualization complete. Total frames: {frame_count}")

        pygame.quit()
        comm.Barrier()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='All-in-One Music Visualization (auto-detects MP3/WAV)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mpiexec -n 4 python3 visualize.py song.mp3
  mpiexec -n 4 python3 visualize.py song.wav --debug
  mpiexec -n 4 python3 visualize.py assets/lone_digger.mp3 --keep-converted
        """
    )
    parser.add_argument(
        'audio_file',
        type=str,
        help='Path to audio file (MP3 or WAV)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug HUD with frame info'
    )
    parser.add_argument(
        '--keep-converted',
        action='store_true',
        help='Keep converted WAV files (don\'t delete temporary files)'
    )

    args = parser.parse_args()

    # Initialize MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Validate MPI configuration
    if size != TOTAL_RANKS:
        if rank == 0:
            print(f"ERROR: This program requires {TOTAL_RANKS} MPI processes (got {size})")
            print(f"Run with: mpiexec -n {TOTAL_RANKS} python3 visualize.py <audio_file>")
        comm.Abort(1)

    # Prepare audio file (auto-detect and convert if needed)
    wav_path = None
    is_temporary = False

    try:
        wav_path, is_temporary = prepare_audio_file(
            args.audio_file,
            keep_converted=args.keep_converted,
            rank=rank
        )

        # Broadcast WAV path to all ranks
        wav_path = comm.bcast(wav_path, root=0)
        is_temporary = comm.bcast(is_temporary, root=0)

        # Run visualization
        run_visualization(wav_path, args.debug, rank, comm)

    except Exception as e:
        if rank == 0:
            print(f"[Rank 0] ERROR: {e}")
            import traceback
            traceback.print_exc()
        comm.Abort(1)

    finally:
        # Cleanup temporary files
        if is_temporary and wav_path and os.path.exists(wav_path):
            if rank == 0:
                print(f"[Rank 0] Cleaning up temporary file: {wav_path}")
                try:
                    os.remove(wav_path)
                except Exception as e:
                    print(f"[Rank 0] Warning: Could not delete temporary file: {e}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Interrupted] Exiting...")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
