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

    Enable neighbor coupling (Part 2):
        mpiexec -n 4 python3 visualize.py song.mp3 --neighbor-coupling

    Cluster deployment:
        mpiexec -n 4 -pernode --machinefile mach_file python3 visualize.py song.mp3

OPTIONS
-------
    --debug                Show debug HUD with frame info, FPS, beat detection
    --keep-converted       Keep temporary converted WAV files (don't auto-delete)
    --neighbor-coupling    Enable Part 2: tiles influence each other's brightness
    --viz-mode MODE        Visualization mode: 'wave' (default) or 'bar'

FEATURES
--------
    Part 1 (Base Implementation):
    - Auto-detects MP3 vs WAV format (by extension and file header)
    - Converts MP3 to WAV (mono, 44.1kHz, 16-bit) automatically if needed
    - Validates WAV format (ensures mono 44.1kHz requirement)
    - Launches synchronized 4-screen MPI visualization (2x2 grid)
    - Real-time audio analysis: STFT, mel filterbank, beat detection
    - Beat-responsive visuals: color changes, height boosts, flash effects
    - 4 color palettes, 4 scene backgrounds (cycle on beats)
    - 30 FPS synchronized rendering across all ranks
    - Auto-cleanup of temporary converted files

    Part 2 (Neighbor Coupling - Optional):
    - Cartesian MPI topology for 2D grid communication
    - Neighbor energy exchange (N/S/E/W) using Sendrecv
    - Brightness modulation based on adjacent tile energies
    - Smoothed neighbor influence (alpha=0.2) to avoid flicker
    - Debug HUD shows local energy and neighbor values

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
    Music-Driven Multi-Screen Visualization Wall (Parts 1 & 2)
    Part 1: Base implementation with synchronized audio-reactive visuals
    Part 2: Neighbor coupling for inter-tile influence (optional flag)
    Using MPI patterns from examples: oneball.py, images.py, bcast.py
"""

import os
import sys
import argparse
import tempfile
import wave
import subprocess
import glob
import curses
import numpy as np
from mpi4py import MPI

# Lazy imports - only load when needed to avoid conflicts
# pygame and visualization modules are loaded only in MPI mode
pygame = None
AudioStream = None
BarVisualizer = None
WaveVisualizer = None
render_debug_hud = None

# Import config (always needed for constants)
from config import *


def _init_visualization_imports():
    """Lazy-load pygame and visualization modules."""
    global pygame, AudioStream, BarVisualizer, WaveVisualizer, render_debug_hud
    if pygame is None:
        import pygame as _pygame
        pygame = _pygame
        from audio import AudioStream as _AudioStream
        from visuals import BarVisualizer as _BarVisualizer, WaveVisualizer as _WaveVisualizer, render_debug_hud as _render_debug_hud
        AudioStream = _AudioStream
        BarVisualizer = _BarVisualizer
        WaveVisualizer = _WaveVisualizer
        render_debug_hud = _render_debug_hud


# ============================================================================
# Launcher UI - File Discovery
# ============================================================================

def discover_machine_files():
    """Find all *_exec machine files in the script directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    files = []
    for f in os.listdir(script_dir):
        if f.endswith('_exec'):
            filepath = os.path.join(script_dir, f)
            # Only include non-empty files
            if os.path.isfile(filepath) and os.path.getsize(filepath) > 0:
                files.append(f)
    return sorted(files)


def discover_audio_files():
    """Find all audio files in assets/ directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, 'assets')
    files = []
    if os.path.isdir(assets_dir):
        for pattern in ['*.wav', '*.mp3']:
            matches = glob.glob(os.path.join(assets_dir, pattern))
            files.extend([os.path.relpath(f, script_dir) for f in matches])
    return sorted(files)


# ============================================================================
# Launcher UI Class (Terminal-based with curses)
# ============================================================================

class TerminalLauncherUI:
    """Curses-based terminal UI for SSH sessions."""

    def __init__(self):
        # Discover available files
        self.machine_files = discover_machine_files()
        self.audio_files = discover_audio_files()
        self.viz_modes = ['wave', 'bar']

        # Fields definition: (display_name, config_key, field_type)
        self.fields = [
            ('Machine File', 'machine_file', 'cycle'),
            ('Audio File', 'audio_file', 'cycle'),
            ('Viz Mode', 'viz_mode', 'cycle'),
            ('Fullscreen', 'fullscreen', 'toggle'),
            ('Debug HUD (show stats)', 'debug', 'toggle'),
            ('Neighbor Coupling', 'neighbor_coupling', 'toggle'),
            ('Keep Converted (MP3)', 'keep_converted', 'toggle'),
        ]

        # Find default indices for paprika_exec and lone_digger.wav
        default_machine_idx = 0
        for i, f in enumerate(self.machine_files):
            if 'paprika' in f.lower():
                default_machine_idx = i
                break

        default_audio_idx = 0
        for i, f in enumerate(self.audio_files):
            if 'lone_digger' in f.lower():
                default_audio_idx = i
                break

        # Configuration state (indices for cycle fields, bools for toggles)
        self.config = {
            'machine_file': default_machine_idx,
            'audio_file': default_audio_idx,
            'viz_mode': 0,
            'fullscreen': True,  # Default ON for cluster
            'debug': False,
            'neighbor_coupling': False,
            'keep_converted': False,
        }

        self.selected_idx = 0  # Currently selected field

    def _get_options_for_field(self, config_key):
        """Get the list of options for a cycle field."""
        if config_key == 'machine_file':
            return self.machine_files
        elif config_key == 'audio_file':
            return self.audio_files
        elif config_key == 'viz_mode':
            return self.viz_modes
        return []

    def _get_display_value(self, config_key):
        """Get the display string for a field's current value."""
        if config_key in ['fullscreen', 'debug', 'neighbor_coupling', 'keep_converted']:
            return 'ON' if self.config[config_key] else 'OFF'
        else:
            options = self._get_options_for_field(config_key)
            idx = self.config[config_key]
            if options and 0 <= idx < len(options):
                return options[idx]
            return '(none)'

    def _adjust_field(self, direction):
        """Adjust the currently selected field by direction (-1 or +1)."""
        _, config_key, field_type = self.fields[self.selected_idx]

        if field_type == 'toggle':
            self.config[config_key] = not self.config[config_key]
        elif field_type == 'cycle':
            options = self._get_options_for_field(config_key)
            if options:
                current = self.config[config_key]
                self.config[config_key] = (current + direction) % len(options)

    def _build_command(self):
        """Build the mpirun command from current configuration."""
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)

        # Get selected values
        machine_file = self.machine_files[self.config['machine_file']] if self.machine_files else None
        audio_file = self.audio_files[self.config['audio_file']] if self.audio_files else None
        viz_mode = self.viz_modes[self.config['viz_mode']]

        if not machine_file or not audio_file:
            return None

        cmd = [
            'mpirun', '-n', '4', '-pernode',
            '-machinefile', os.path.join(script_dir, machine_file),
            'python3', script_path,
            os.path.join(script_dir, audio_file),
            '--viz-mode', viz_mode,
        ]

        if self.config['fullscreen']:
            cmd.append('--fullscreen')
        if self.config['debug']:
            cmd.append('--debug')
        if self.config['neighbor_coupling']:
            cmd.append('--neighbor-coupling')
        if self.config['keep_converted']:
            cmd.append('--keep-converted')

        return cmd

    def _draw(self, stdscr):
        """Draw the UI using curses."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Title
        title = "MUSIC VISUALIZATION LAUNCHER"
        if width > len(title):
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD)

        # Controls hint
        hint = "UP/DOWN: navigate | LEFT/RIGHT: change | ENTER: launch | Q: quit"
        if width > len(hint):
            stdscr.addstr(2, (width - len(hint)) // 2, hint, curses.A_DIM)

        # Fields
        start_y = 5
        for i, (display_name, config_key, _) in enumerate(self.fields):
            if start_y + i >= height - 5:
                break  # Don't draw past screen

            is_selected = (i == self.selected_idx)
            prefix = "> " if is_selected else "  "
            value = self._get_display_value(config_key)
            line = f"{prefix}{display_name:20} < {value} >"

            # Truncate if too wide
            if len(line) > width - 8:
                line = line[:width - 11] + "..."

            attr = curses.A_REVERSE if is_selected else curses.A_NORMAL
            try:
                stdscr.addstr(start_y + i, 4, line, attr)
            except curses.error:
                pass  # Ignore if can't write (terminal too small)

        # Command preview
        cmd_y = start_y + len(self.fields) + 2
        if cmd_y < height - 3:
            separator = "-" * min(width - 8, 60)
            try:
                stdscr.addstr(cmd_y, 4, separator, curses.A_DIM)
            except curses.error:
                pass

            cmd = self._build_command()
            if cmd:
                try:
                    stdscr.addstr(cmd_y + 1, 4, "Command:", curses.A_DIM)
                except curses.error:
                    pass

                cmd_str = ' '.join(cmd)
                max_width = width - 8
                # Wrap command across multiple lines
                line_num = 0
                for start in range(0, len(cmd_str), max_width):
                    if cmd_y + 2 + line_num < height - 1:
                        try:
                            stdscr.addstr(cmd_y + 2 + line_num, 4, cmd_str[start:start + max_width])
                        except curses.error:
                            pass
                    line_num += 1
                    if line_num >= 3:  # Max 3 lines
                        break
            else:
                try:
                    stdscr.addstr(cmd_y + 1, 4, "Error: No machine file or audio file found", curses.A_BOLD)
                except curses.error:
                    pass

        stdscr.refresh()

    def _run_curses(self, stdscr):
        """Main curses loop."""
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)  # Enable arrow keys

        while True:
            self._draw(stdscr)
            key = stdscr.getch()

            if key == curses.KEY_UP:
                self.selected_idx = (self.selected_idx - 1) % len(self.fields)
            elif key == curses.KEY_DOWN:
                self.selected_idx = (self.selected_idx + 1) % len(self.fields)
            elif key == curses.KEY_LEFT:
                self._adjust_field(-1)
            elif key == curses.KEY_RIGHT:
                self._adjust_field(1)
            elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER, 10, 13):
                cmd = self._build_command()
                if cmd:
                    return cmd
            elif key in (ord('q'), ord('Q'), 27):  # q, Q, or ESC
                return None

    def run(self):
        """Run the UI and return command or None."""
        return curses.wrapper(self._run_curses)


def launch_mpi_visualization(cmd):
    """Launch MPI visualization via subprocess."""
    print("=" * 60)
    print("Launching MPI Visualization")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Run subprocess directly without capturing output
        # This allows real-time output and proper terminal handling
        result = subprocess.run(cmd, cwd=script_dir)

        if result.returncode != 0:
            print(f"ERROR: mpirun exited with code {result.returncode}")
            return result.returncode

        print("Visualization completed.")
        return 0
    except FileNotFoundError:
        print("ERROR: 'mpirun' not found. Is MPI installed?")
        return 1
    except Exception as e:
        print(f"ERROR: Failed to launch: {e}")
        import traceback
        traceback.print_exc()
        return 1


def run_launcher_ui():
    """Run the terminal launcher UI and launch visualization if configured."""
    launcher = TerminalLauncherUI()
    cmd = launcher.run()

    if cmd:
        return launch_mpi_visualization(cmd)
    else:
        print("Cancelled.")
        return 0


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

    # Lazy import pygame for conversion
    _init_visualization_imports()

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
# Part 2: Neighbor Coupling
# ============================================================================

def exchange_neighbor_energy(cart, local_bands, nbr_smooth, alpha):
    """
    Exchange local energy with neighbors and update smoothed values.
    (Part 2: Neighbor Coupling)

    Args:
        cart: MPI Cartesian communicator
        local_bands: numpy array of local mel band energies
        nbr_smooth: dict of smoothed neighbor energies {"N":0.0, "S":0.0, "W":0.0, "E":0.0}
        alpha: smoothing factor (0-1)

    Returns:
        tuple (local_energy, updated nbr_smooth dict)
    """
    # Calculate local energy (mean of local bands)
    local_energy = float(local_bands.mean())

    # Prepare send buffer
    send_buf = np.array([local_energy], dtype=np.float32)

    # Exchange with each neighbor: N, S, W, E
    # Cartesian topology: dim 0 = rows (N/S), dim 1 = cols (W/E)
    neighbors = [
        (0, -1, "N"),  # North: row dim, shift -1
        (0,  1, "S"),  # South: row dim, shift +1
        (1, -1, "W"),  # West: col dim, shift -1
        (1,  1, "E"),  # East: col dim, shift +1
    ]

    for dim, disp, key in neighbors:
        # Get source and destination ranks
        src, dst = cart.Shift(dim, disp)

        # Receive buffer
        recv_buf = np.zeros(1, dtype=np.float32)

        # Exchange if neighbor exists (not PROC_NULL)
        if dst != MPI.PROC_NULL and src != MPI.PROC_NULL:
            cart.Sendrecv(
                sendbuf=send_buf, dest=dst,
                recvbuf=recv_buf, source=src
            )
            # Smooth the received value
            nbr_smooth[key] = (1.0 - alpha) * nbr_smooth[key] + alpha * recv_buf[0]
        else:
            # No neighbor in this direction (edge of grid)
            nbr_smooth[key] = 0.0

    return local_energy, nbr_smooth


# ============================================================================
# MPI Visualization Setup
# ============================================================================

def setup_pygame_window(rank, fullscreen=False):
    """
    Initialize pygame and create window for this rank.

    Args:
        rank: MPI rank (0-3)
        fullscreen: If True, use fullscreen mode (for cluster deployment)

    Returns:
        tuple (screen, clock, screen_width, screen_height)
    """
    # Set display
    os.environ['DISPLAY'] = ':0.0'

    # Initialize pygame
    pygame.display.init()
    pygame.font.init()
    pygame.mouse.set_visible(False)

    if fullscreen:
        # Fullscreen mode: each node fills its entire screen
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen_width = screen.get_width()
        screen_height = screen.get_height()
    else:
        # Windowed mode: position windows in 2x2 grid on single display
        pos = WINDOW_POSITIONS[rank]
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos[0]},{pos[1]}"
        screen = pygame.display.set_mode(
            (WIN_W, WIN_H),
            pygame.NOFRAME  # Borderless
        )
        screen_width = WIN_W
        screen_height = WIN_H

    pygame.display.set_caption(f"Music Visualization - Rank {rank}")

    # Create clock
    clock = pygame.time.Clock()

    return screen, clock, screen_width, screen_height


# ============================================================================
# Main Visualization Loop
# ============================================================================

def run_visualization(wav_path, debug=False, neighbor_coupling=False, viz_mode='wave', fullscreen=False, rank=0, comm=None):
    """
    Run the main MPI visualization loop.

    Args:
        wav_path: Path to WAV file
        debug: Show debug HUD
        neighbor_coupling: Enable Part 2 neighbor coupling (default=False)
        viz_mode: Visualization mode ('wave' or 'bar')
        fullscreen: Use fullscreen mode (for cluster deployment)
        rank: MPI rank
        comm: MPI communicator
    """
    # Initialize pygame and visualization modules (lazy import)
    _init_visualization_imports()

    # Setup pygame window
    screen, clock, screen_width, screen_height = setup_pygame_window(rank, fullscreen)

    if rank == 0:
        print(f"[Rank 0] Screen size: {screen_width}x{screen_height} (fullscreen={fullscreen})")

    # Initialize visualizer based on mode
    if viz_mode == 'wave':
        visualizer = WaveVisualizer(rank, screen_width, screen_height)
        if rank == 0:
            print("[Rank 0] Part 3: Wave visualization mode")
    else:
        visualizer = BarVisualizer(rank, screen_width, screen_height)
        if rank == 0:
            print("[Rank 0] Using bar visualization mode")

    # Font for debug HUD
    debug_font = pygame.font.SysFont('monospace', 12) if debug else None

    # Part 2: Setup Cartesian topology if neighbor coupling enabled
    cart = None
    nbr_smooth = None
    if neighbor_coupling:
        # Create 2D Cartesian topology (2x2 grid, non-periodic)
        cart = comm.Create_cart((GRID_P, GRID_Q), periods=(False, False), reorder=False)
        # Initialize smoothed neighbor energy dict
        nbr_smooth = {"N": 0.0, "S": 0.0, "W": 0.0, "E": 0.0}
        if rank == 0:
            print("[Rank 0] Part 2: Neighbor coupling enabled")

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
            # PART 2: Neighbor Coupling (if enabled)
            # ================================================================
            neighbor_brightness = 1.0
            neighbor_debug_data = None

            if neighbor_coupling and cart is not None and nbr_smooth is not None:
                # Get local band slice for this rank
                all_bands = frame_data['bands']
                band_start = rank * BANDS_PER_RANK
                band_end = (rank + 1) * BANDS_PER_RANK
                local_bands = all_bands[band_start:band_end]

                # Exchange energy with neighbors
                local_energy, nbr_smooth = exchange_neighbor_energy(
                    cart, local_bands, nbr_smooth, NEIGHBOR_COUPLING_ALPHA
                )

                # Calculate brightness modulation
                max_neighbor = max(nbr_smooth.values())
                neighbor_brightness = NEIGHBOR_BASE_BRIGHTNESS * (
                    1.0 + NEIGHBOR_COUPLING_K * max_neighbor
                )

                # Prepare debug data
                neighbor_debug_data = {
                    'local_energy': local_energy,
                    'neighbors': nbr_smooth.copy(),
                    'brightness': neighbor_brightness
                }

            # ================================================================
            # ALL RANKS: Render visualization
            # ================================================================
            visualizer.render(screen, frame_data, neighbor_brightness=neighbor_brightness)

            # Render debug HUD if enabled
            if debug:
                render_debug_hud(screen, frame_data, rank, debug_font, neighbor_data=neighbor_debug_data)

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
    # Initialize MPI first to check mode
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # ========================================================================
    # LAUNCHER MODE: If running without MPI (size == 1) and no arguments
    # ========================================================================
    if size == 1 and len(sys.argv) == 1:
        # No MPI, no arguments -> show launcher UI
        return run_launcher_ui()

    # ========================================================================
    # ERROR: Running without MPI but with arguments
    # ========================================================================
    if size == 1 and len(sys.argv) > 1:
        print(f"ERROR: This program requires {TOTAL_RANKS} MPI processes (got {size})")
        print(f"Run with: mpirun -n {TOTAL_RANKS} python3 visualize.py <audio_file>")
        print(f"Or run without arguments to use the launcher UI: python3 visualize.py")
        return 1

    # ========================================================================
    # MPI MODE: Running with MPI
    # ========================================================================

    # Validate MPI configuration
    if size != TOTAL_RANKS:
        if rank == 0:
            print(f"ERROR: This program requires {TOTAL_RANKS} MPI processes (got {size})")
            print(f"Run with: mpiexec -n {TOTAL_RANKS} python3 visualize.py <audio_file>")
        comm.Abort(1)

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
    parser.add_argument(
        '--neighbor-coupling',
        action='store_true',
        help='Enable Part 2 neighbor coupling (tiles influence each other)'
    )
    parser.add_argument(
        '--viz-mode',
        type=str,
        choices=['wave', 'bar'],
        default='wave',
        help='Visualization mode: wave (default) or bar'
    )
    parser.add_argument(
        '--fullscreen',
        action='store_true',
        help='Fullscreen mode (for cluster deployment where each node has its own screen)'
    )

    args = parser.parse_args()

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
        run_visualization(
            wav_path,
            debug=args.debug,
            neighbor_coupling=args.neighbor_coupling,
            viz_mode=args.viz_mode,
            fullscreen=args.fullscreen,
            rank=rank,
            comm=comm
        )

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
        if pygame is not None:
            pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if pygame is not None:
            pygame.quit()
        sys.exit(1)
