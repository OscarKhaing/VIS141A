#!/usr/bin/env python3
"""
Music-Driven Multi-Screen Visualization Wall
Part 1: Base Implementation

Main orchestrator for synchronized 4-screen (2x2 grid) audio visualization.
Rank 0 reads audio and broadcasts analysis frames to all ranks for rendering.

Usage:
    mpiexec -n 4 python3 wall.py --audio assets/track.wav [--debug]
"""

import os
import sys
import argparse
import pygame
import numpy as np
from mpi4py import MPI

# Import local modules
from config import *
from audio import AudioStream
from visuals import BarVisualizer, render_debug_hud


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Music-Driven Multi-Screen Visualization Wall'
    )
    parser.add_argument(
        '--audio',
        type=str,
        required=True,
        help='Path to audio file (mono WAV, 44.1kHz)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug HUD with frame info'
    )
    parser.add_argument(
        '--fullscreen',
        action='store_true',
        help='Run in fullscreen mode'
    )
    return parser.parse_args()


def setup_pygame_window(rank):
    """
    Initialize pygame and create window for this rank.

    Args:
        rank: MPI rank (0-3)

    Returns:
        tuple (screen, clock) - pygame Surface and Clock
    """
    # Set display (important for remote/headless setups)
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
        pygame.NOFRAME  # Borderless for seamless multi-screen
    )
    pygame.display.set_caption(f"Music Wall - Rank {rank}")

    # Create clock for FPS control
    clock = pygame.time.Clock()

    return screen, clock


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()

    # Initialize MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Validate MPI configuration
    assert size == TOTAL_RANKS, (
        f"This program requires {TOTAL_RANKS} MPI processes (got {size}). "
        f"Run with: mpiexec -n {TOTAL_RANKS} python3 wall.py --audio <file>"
    )

    # Setup pygame window
    screen, clock = setup_pygame_window(rank)

    # Initialize visualizer
    visualizer = BarVisualizer(rank, WIN_W, WIN_H)

    # Font for debug HUD (if needed)
    debug_font = pygame.font.SysFont('monospace', 12) if args.debug else None

    # Rank 0: Initialize audio stream
    audio_stream = None
    if rank == 0:
        print(f"[Rank 0] Loading audio: {args.audio}")
        try:
            audio_stream = AudioStream(args.audio)
            print(f"[Rank 0] Audio loaded: {audio_stream.total_samples} samples "
                  f"({audio_stream.total_samples / SR:.2f}s)")
        except Exception as e:
            print(f"[Rank 0] ERROR loading audio: {e}")
            comm.Abort(1)

    # Synchronize before starting main loop
    comm.Barrier()
    if rank == 0:
        print("[Rank 0] Starting visualization...")

    # Main loop
    running = True
    frame_count = 0
    frame_data = None

    while running:
        # ====================================================================
        # BARRIER: Synchronize all ranks at frame boundary
        # ====================================================================
        comm.Barrier()

        # ====================================================================
        # RANK 0: Read audio and broadcast frame data
        # ====================================================================
        if rank == 0:
            # Get next audio analysis frame
            frame_data = audio_stream.get_next_frame()

            # Check for end of stream
            if frame_data['eos']:
                print("[Rank 0] End of audio stream reached")
                running = False

            # Broadcast frame data to all ranks
            frame_data = comm.bcast(frame_data, root=0)
        else:
            # Other ranks: Receive frame data
            frame_data = comm.bcast(None, root=0)

        # Check if we should stop
        if frame_data and frame_data.get('eos', False):
            running = False
            break

        # ====================================================================
        # ALL RANKS: Render visualization
        # ====================================================================
        visualizer.render(screen, frame_data)

        # Render debug HUD if enabled
        if args.debug:
            render_debug_hud(screen, frame_data, rank, debug_font)

        # Update display
        pygame.display.update()

        # ====================================================================
        # EVENT HANDLING: Check for quit
        # ====================================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False

        # ====================================================================
        # FRAME RATE CONTROL
        # ====================================================================
        clock.tick(TARGET_FPS)
        frame_count += 1

        # Optional: Print FPS stats periodically
        if rank == 0 and frame_count % 100 == 0:
            actual_fps = clock.get_fps()
            print(f"[Rank 0] Frame {frame_count}, FPS: {actual_fps:.1f}, "
                  f"Time: {frame_data.get('t_sec', 0):.2f}s")

    # ====================================================================
    # CLEANUP
    # ====================================================================
    comm.Barrier()  # Ensure all ranks finish together

    if rank == 0:
        print(f"[Rank 0] Visualization complete. Total frames: {frame_count}")

    pygame.quit()
    comm.Barrier()


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
