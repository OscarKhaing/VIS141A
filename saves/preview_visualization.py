#!/usr/bin/env python3
"""
Visualization Preview Generator
===============================

Generates static screenshots of the music visualization at key moments without
requiring MPI or display setup. Useful for design iteration and previewing.

USAGE
-----
    Auto-capture 4 interesting moments:
        python3 preview_visualization.py song.mp3

    Capture at specific timestamps:
        python3 preview_visualization.py song.mp3 --times 10.5 30.2 60.8 120.0

    Save individual rank images:
        python3 preview_visualization.py song.mp3 --individual-ranks

    Custom output directory:
        python3 preview_visualization.py song.mp3 --output-dir ./my_previews/

EXAMPLES
--------
    Basic preview:
        python3 preview_visualization.py assets/lone_digger.mp3

    Design iteration (force palette):
        python3 preview_visualization.py assets/lone_digger.mp3 --palette 2

    Documentation screenshots:
        python3 preview_visualization.py assets/lone_digger.mp3 --times 30 60 90 --show-grid

OUTPUT
------
    Creates PNG files in output directory (default: ./previews/)
    Format: {basename}_grid_{index:04d}_{time:.1f}s.png

FEATURES
--------
    - No MPI required (single process)
    - Offscreen rendering (headless)
    - Auto-detects interesting moments (beats, energy peaks)
    - Generates full 2×2 grid composite images
    - Optional individual rank screenshots
    - Reuses audio.py and visuals.py pipelines
"""

import os
import sys
import argparse
import numpy as np
import pygame
from pathlib import Path

# Import local modules
from config import *
from audio import AudioStream
from visuals import BarVisualizer, WaveVisualizer


def find_interesting_moments(audio_stream, num_samples=4):
    """
    Analyze audio and find interesting moments for screenshots.

    Strategy:
    - First strong beat
    - Maximum energy moment
    - Evenly spaced throughout song
    - High spectral flux moments

    Args:
        audio_stream: AudioStream object
        num_samples: Number of timestamps to return

    Returns:
        List of timestamps (seconds) sorted chronologically
    """
    print("Analyzing audio to find interesting moments...")

    # Collect data: flux values and timestamps
    flux_values = []
    timestamps = []
    beat_times = []

    tick = 0
    while True:
        frame = audio_stream.get_next_frame()
        if frame['eos']:
            break

        flux_values.append(frame['flux'])
        timestamps.append(frame['t_sec'])

        if frame['beat']:
            beat_times.append(frame['t_sec'])

        tick += 1

    flux_values = np.array(flux_values)
    timestamps = np.array(timestamps)

    print(f"  Total duration: {timestamps[-1]:.1f}s")
    print(f"  Detected {len(beat_times)} beats")

    # Strategy: Pick diverse interesting moments
    selected_times = []

    # 1. First strong beat (after 5s to skip silence)
    early_beats = [t for t in beat_times if t > 5.0]
    if early_beats:
        selected_times.append(early_beats[0])

    # 2. Maximum energy moment
    max_flux_idx = np.argmax(flux_values)
    selected_times.append(timestamps[max_flux_idx])

    # 3. Evenly distributed samples
    duration = timestamps[-1]
    for i in range(1, num_samples - 1):
        ratio = i / (num_samples - 1)
        time = duration * ratio
        selected_times.append(time)

    # Sort and deduplicate
    selected_times = sorted(set(selected_times))

    # Trim to requested number
    if len(selected_times) > num_samples:
        # Keep first, last, and evenly spaced middle ones
        indices = np.linspace(0, len(selected_times) - 1, num_samples).astype(int)
        selected_times = [selected_times[i] for i in indices]

    return selected_times[:num_samples]


def seek_to_time(audio_stream, target_time):
    """
    Advance audio stream to specific timestamp.

    Args:
        audio_stream: AudioStream object
        target_time: Target time in seconds

    Returns:
        frame_data dict at target time
    """
    frame = None
    while True:
        frame = audio_stream.get_next_frame()
        if frame['eos'] or frame['t_sec'] >= target_time:
            break
    return frame


def render_grid_composite(frame_data, palette_override=None, show_grid=False, viz_mode='wave'):
    """
    Render full 2×2 grid composite with all 4 ranks.

    Args:
        frame_data: Frame data dict with bands, beat, scene, palette
        palette_override: Force specific palette (0-3) or None
        show_grid: Draw grid lines between ranks
        viz_mode: Visualization mode ('wave' or 'bar')

    Returns:
        pygame.Surface with full composite (1920×1080)
    """
    # Create full-size surface
    full_width = WIN_W * GRID_Q
    full_height = WIN_H * GRID_P
    composite = pygame.Surface((full_width, full_height))

    # Override palette if requested
    if palette_override is not None:
        frame_data = frame_data.copy()
        frame_data['palette'] = palette_override

    # Render each rank
    for rank in range(TOTAL_RANKS):
        # Create visualizer for this rank based on mode
        if viz_mode == 'wave':
            visualizer = WaveVisualizer(rank, WIN_W, WIN_H)
        else:
            visualizer = BarVisualizer(rank, WIN_W, WIN_H)

        # Create offscreen surface
        screen = pygame.Surface((WIN_W, WIN_H))

        # Render
        visualizer.render(screen, frame_data)

        # Blit to composite at correct position
        pos = WINDOW_POSITIONS[rank]
        composite.blit(screen, pos)

    # Draw grid lines (always visible, thicker if show_grid=True)
    if show_grid:
        # Thick bright lines for documentation
        grid_color = (150, 150, 150)
        line_width = 4
    else:
        # Thin subtle lines by default (always present)
        grid_color = (80, 80, 80)
        line_width = 2

    # Vertical line (separates left/right)
    pygame.draw.line(composite, grid_color, (WIN_W, 0), (WIN_W, full_height), line_width)
    # Horizontal line (separates top/bottom)
    pygame.draw.line(composite, grid_color, (0, WIN_H), (full_width, WIN_H), line_width)

    # Add rank labels in corners (subtle but visible)
    font = pygame.font.SysFont('monospace', 14, bold=True)
    label_color = (200, 200, 200)
    labels = [
        (0, "Rank 0: BASS", (10, 10)),
        (1, "Rank 1: LOW-MID", (WIN_W + 10, 10)),
        (2, "Rank 2: MID", (10, WIN_H + 10)),
        (3, "Rank 3: HIGH", (WIN_W + 10, WIN_H + 10))
    ]

    for rank, text, pos in labels:
        text_surface = font.render(text, True, label_color)
        composite.blit(text_surface, pos)

    return composite


def render_individual_rank(frame_data, rank, palette_override=None, viz_mode='wave'):
    """
    Render single rank visualization.

    Args:
        frame_data: Frame data dict
        rank: Rank number (0-3)
        palette_override: Force specific palette or None
        viz_mode: Visualization mode ('wave' or 'bar')

    Returns:
        pygame.Surface with rank visualization
    """
    # Override palette if requested
    if palette_override is not None:
        frame_data = frame_data.copy()
        frame_data['palette'] = palette_override

    # Create visualizer based on mode
    if viz_mode == 'wave':
        visualizer = WaveVisualizer(rank, WIN_W, WIN_H)
    else:
        visualizer = BarVisualizer(rank, WIN_W, WIN_H)

    # Create offscreen surface
    screen = pygame.Surface((WIN_W, WIN_H))

    # Render
    visualizer.render(screen, frame_data)

    return screen


def save_screenshot(surface, output_path):
    """
    Save pygame surface as PNG.

    Args:
        surface: pygame.Surface
        output_path: Output file path
    """
    pygame.image.save(surface, output_path)
    print(f"  Saved: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate visualization preview screenshots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 preview_visualization.py song.mp3
  python3 preview_visualization.py song.mp3 --times 10.5 30.2 60.8
  python3 preview_visualization.py song.mp3 --palette 2 --show-grid
        """
    )
    parser.add_argument(
        'audio_file',
        type=str,
        help='Path to audio file (MP3 or WAV)'
    )
    parser.add_argument(
        '--times',
        type=float,
        nargs='+',
        help='Specific timestamps (seconds) to capture'
    )
    parser.add_argument(
        '--num-samples',
        type=int,
        default=4,
        help='Number of auto-selected moments (default: 4)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./previews',
        help='Output directory for screenshots (default: ./previews)'
    )
    parser.add_argument(
        '--individual-ranks',
        action='store_true',
        help='Save individual rank images in addition to grid'
    )
    parser.add_argument(
        '--palette',
        type=int,
        choices=[0, 1, 2, 3],
        help='Force specific palette (0-3)'
    )
    parser.add_argument(
        '--show-grid',
        action='store_true',
        help='Draw thicker/brighter grid lines (subtle lines always present)'
    )
    parser.add_argument(
        '--viz-mode',
        type=str,
        choices=['wave', 'bar'],
        default='wave',
        help='Visualization mode: wave (default) or bar'
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.audio_file):
        print(f"ERROR: Audio file not found: {args.audio_file}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get base filename
    base_name = Path(args.audio_file).stem

    # Initialize pygame (headless)
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.init()
    pygame.display.init()
    pygame.font.init()

    print("=" * 70)
    print("Visualization Preview Generator")
    print("=" * 70)
    print(f"Input: {args.audio_file}")
    print(f"Output: {output_dir}/")
    print(f"Mode: {args.viz_mode}")
    print()

    # Load audio
    print("Loading audio...")
    audio_stream = AudioStream(args.audio_file)
    duration = audio_stream.total_samples / SR
    print(f"  Duration: {duration:.1f}s ({int(duration//60)}m {int(duration%60)}s)")
    print()

    # Determine capture times
    if args.times:
        capture_times = sorted(args.times)
        print(f"Capturing at manual timestamps: {capture_times}")
    else:
        capture_times = find_interesting_moments(audio_stream, args.num_samples)
        print(f"Auto-selected capture times: {[f'{t:.1f}s' for t in capture_times]}")

    print()

    # Reset audio stream for capture
    audio_stream = AudioStream(args.audio_file)

    # Capture screenshots
    print("Generating screenshots...")
    for idx, target_time in enumerate(capture_times, 1):
        print(f"\n[{idx}/{len(capture_times)}] Capturing at {target_time:.1f}s...")

        # Seek to target time
        frame_data = seek_to_time(audio_stream, target_time)

        if frame_data['eos']:
            print(f"  WARNING: Reached end of stream before {target_time:.1f}s")
            break

        actual_time = frame_data['t_sec']
        print(f"  Actual time: {actual_time:.1f}s")
        print(f"  Beat: {'YES' if frame_data['beat'] else 'no'}")
        print(f"  Flux: {frame_data['flux']:.3f}")

        # Generate grid composite
        grid_surface = render_grid_composite(
            frame_data,
            palette_override=args.palette,
            show_grid=args.show_grid,
            viz_mode=args.viz_mode
        )

        # Save grid composite
        grid_filename = f"{base_name}_grid_{idx:04d}_{actual_time:.1f}s.png"
        grid_path = output_dir / grid_filename
        save_screenshot(grid_surface, str(grid_path))

        # Save individual ranks if requested
        if args.individual_ranks:
            for rank in range(TOTAL_RANKS):
                rank_surface = render_individual_rank(
                    frame_data,
                    rank,
                    palette_override=args.palette,
                    viz_mode=args.viz_mode
                )
                rank_filename = f"{base_name}_rank{rank}_{idx:04d}_{actual_time:.1f}s.png"
                rank_path = output_dir / rank_filename
                save_screenshot(rank_surface, str(rank_path))

    print()
    print("=" * 70)
    print("✓ Preview generation complete!")
    print(f"  Output directory: {output_dir}/")
    print(f"  Generated {len(capture_times)} screenshot(s)")
    print("=" * 70)

    pygame.quit()


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
