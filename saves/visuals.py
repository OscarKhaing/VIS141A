"""
Visualization rendering module for music-driven multi-screen wall.
Part 1: Base Implementation
"""

import pygame
import numpy as np
from config import *


class BarVisualizer:
    """
    Renders frequency bars for assigned mel band slice.
    Supports beat effects, palette changes, and scene transitions.
    """

    def __init__(self, rank, screen_width=WIN_W, screen_height=WIN_H):
        """
        Initialize bar visualizer.

        Args:
            rank: MPI rank (0-3)
            screen_width: Width of screen in pixels
            screen_height: Height of screen in pixels
        """
        self.rank = rank
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Calculate band slice for this rank
        self.band_start = rank * BANDS_PER_RANK
        self.band_end = (rank + 1) * BANDS_PER_RANK
        self.n_bands = BANDS_PER_RANK

        # Calculate bar geometry
        total_spacing = BAR_SPACING * (self.n_bands - 1)
        self.bar_width = (screen_width - total_spacing) // self.n_bands
        self.bar_spacing = BAR_SPACING

        # Cache bar x positions
        self.bar_x_positions = []
        x = 0
        for i in range(self.n_bands):
            self.bar_x_positions.append(x)
            x += self.bar_width + self.bar_spacing

        # Beat effect state
        self.beat_boost_current = 1.0
        self.beat_glow = 0.0

        # Smoothed band values for attack/decay motion
        self.smoothed_bands = np.zeros(self.n_bands, dtype=np.float32)

    def _smooth_bands(self, new_bands):
        """
        Apply attack/decay smoothing to band values.
        Fast attack (responsive to increases), slow decay (peaks hang in air).

        Args:
            new_bands: numpy array of new band energies

        Returns:
            numpy array of smoothed band values
        """
        for i in range(len(new_bands)):
            if new_bands[i] > self.smoothed_bands[i]:
                # Attack: fast response to increases
                alpha = ATTACK_ALPHA
            else:
                # Decay: slow fall-off, peaks linger
                alpha = DECAY_ALPHA
            self.smoothed_bands[i] = (1 - alpha) * self.smoothed_bands[i] + alpha * new_bands[i]
        return self.smoothed_bands.copy()

    def render(self, screen, frame_data, neighbor_brightness=1.0):
        """
        Render visualization frame.

        Args:
            screen: pygame Surface to render to
            frame_data: dict containing:
                - 'bands': full mel band array
                - 'beat': beat flag
                - 'scene': scene index
                - 'palette': palette index
            neighbor_brightness: brightness multiplier from neighbor coupling (default=1.0)
        """
        # Extract parameters
        all_bands = frame_data['bands']
        beat = frame_data['beat']
        scene = frame_data['scene']
        palette_idx = frame_data['palette']

        # Get assigned band slice
        bands_slice = all_bands[self.band_start:self.band_end]

        # Apply temporal smoothing (attack/decay) for smooth motion
        bands_slice = self._smooth_bands(bands_slice)

        # Apply neighbor brightness modulation (Part 2)
        bands_slice = bands_slice * neighbor_brightness

        # Update beat effect
        if beat:
            self.beat_boost_current = BEAT_BOOST
            self.beat_glow = 1.0
        else:
            self.beat_boost_current = max(1.0, self.beat_boost_current * BEAT_DECAY)
            self.beat_glow = max(0.0, self.beat_glow * BEAT_DECAY)

        # Get background color
        bg_color = BACKGROUNDS[scene % len(BACKGROUNDS)]

        # Fill background
        screen.fill(bg_color)

        # Get palette
        palette = PALETTES[palette_idx % len(PALETTES)]

        # Render bars
        self._render_bars(screen, bands_slice, palette)

        # Render beat flash overlay
        if self.beat_glow > 0.1:
            self._render_beat_flash(screen)

    def _render_bars(self, screen, bands, palette):
        """
        Render frequency bars.

        Args:
            screen: pygame Surface
            bands: mel band energies for this rank's slice
            palette: list of RGB tuples
        """
        for i, energy in enumerate(bands):
            # Calculate bar height
            height = max(BAR_MIN_HEIGHT, energy * BAR_SCALE * self.beat_boost_current)
            height = min(height, self.screen_height)  # Clamp to screen height

            # Bar position (grow from bottom)
            x = self.bar_x_positions[i]
            y = self.screen_height - int(height)

            # Choose color from palette (cycle through)
            color_idx = i % len(palette)
            color = palette[color_idx]

            # Boost color brightness on beat
            if self.beat_glow > 0.1:
                color = self._brighten_color(color, 1.0 + 0.3 * self.beat_glow)

            # Draw bar
            rect = pygame.Rect(x, y, self.bar_width, int(height))
            pygame.draw.rect(screen, color, rect)

            # Draw highlight on top (lighter version)
            if height > BAR_MIN_HEIGHT * 2:
                highlight_color = self._brighten_color(color, 1.3)
                highlight_height = max(2, int(height * 0.1))
                highlight_rect = pygame.Rect(x, y, self.bar_width, highlight_height)
                pygame.draw.rect(screen, highlight_color, highlight_rect)

    def _render_beat_flash(self, screen):
        """
        Render a semi-transparent white flash on beat.

        Args:
            screen: pygame Surface
        """
        flash_alpha = int(self.beat_glow * 40)  # Max 40 alpha
        flash_surface = pygame.Surface((self.screen_width, self.screen_height))
        flash_surface.set_alpha(flash_alpha)
        flash_surface.fill((255, 255, 255))
        screen.blit(flash_surface, (0, 0))

    def _brighten_color(self, color, factor):
        """
        Brighten an RGB color by a factor.

        Args:
            color: (r, g, b) tuple
            factor: brightness multiplier (>1.0 brightens)

        Returns:
            (r, g, b) tuple with values clamped to [0, 255]
        """
        r, g, b = color
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return (r, g, b)


class WaveVisualizer:
    """
    Renders continuous wave visualization across all 4 panels.
    Part 3: Wave Visualization

    Layout:
    - Top row (ranks 0, 1): Wave grows upward from bottom edge
    - Bottom row (ranks 2, 3): Wave grows downward from top edge (mirrored)
    - Creates vertical symmetry across the horizontal center line
    """

    def __init__(self, rank, screen_width=WIN_W, screen_height=WIN_H):
        """
        Initialize wave visualizer.

        Args:
            rank: MPI rank (0-3)
            screen_width: Width of screen in pixels
            screen_height: Height of screen in pixels
        """
        self.rank = rank
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Determine position in grid
        self.is_top_row = rank < 2       # Ranks 0, 1 are top
        self.is_left_col = rank % 2 == 0  # Ranks 0, 2 are left

        # Global X offset for this rank's portion (based on actual screen width)
        self.global_x_offset = 0 if self.is_left_col else screen_width

        # Wave rendering parameters
        self.num_points = N_MELS  # 96 points on the wave
        self.total_width = screen_width * GRID_Q  # Total width across all columns

        # Beat effect state
        self.beat_boost = 1.0
        self.beat_glow = 0.0

        # Smoothed band values for attack/decay motion
        self.smoothed_bands = np.zeros(N_MELS, dtype=np.float32)

        # Dynamic scale factor (auto-adjusts so max peak reaches target height)
        self.dynamic_scale = WAVE_SCALE  # Start at default

    def _smooth_bands(self, new_bands):
        """
        Apply attack/decay smoothing to band values.
        Fast attack (responsive to increases), slow decay (peaks hang in air).

        Args:
            new_bands: numpy array of new band energies

        Returns:
            numpy array of smoothed band values
        """
        for i in range(len(new_bands)):
            if new_bands[i] > self.smoothed_bands[i]:
                # Attack: fast response to increases
                alpha = ATTACK_ALPHA
            else:
                # Decay: slow fall-off, peaks linger
                alpha = DECAY_ALPHA
            self.smoothed_bands[i] = (1 - alpha) * self.smoothed_bands[i] + alpha * new_bands[i]
        return self.smoothed_bands.copy()

    def _horizontal_smooth(self, bands):
        """
        Apply horizontal smoothing to reduce pointiness between adjacent bands.
        Uses convolution with a smoothing kernel applied multiple passes.

        Args:
            bands: numpy array of band energies

        Returns:
            numpy array of horizontally smoothed band values
        """
        # Use 5-point kernel for nice smooth curves
        kernel = np.array(WAVE_SMOOTH_KERNEL_5, dtype=np.float32)
        half_k = len(kernel) // 2

        result = bands.copy()

        # Apply smoothing multiple passes for extra roundness
        for _ in range(WAVE_SMOOTH_PASSES):
            # Pad edges to maintain array length
            padded = np.pad(result, (half_k, half_k), mode='edge')
            # Convolve and extract valid region
            result = np.convolve(padded, kernel, mode='valid')

        return result

    def _compute_dynamic_scale(self, bands):
        """
        Compute dynamic scale factor so max peak reaches target screen height.
        Uses smoothed adjustment to avoid jarring changes.

        Args:
            bands: numpy array of band energies (after smoothing)
        """
        # Find current max energy
        max_energy = np.max(bands)
        if max_energy < 0.001:
            return  # Avoid division by zero during silence

        # Target amplitude (45% of screen height)
        target_amplitude = self.screen_height * WAVE_TARGET_HEIGHT_RATIO

        # Calculate ideal scale to reach target height
        # amplitude = energy * scale * beat_boost
        # target = max_energy * ideal_scale * beat_boost
        # ideal_scale = target / (max_energy * beat_boost)
        ideal_scale = target_amplitude / (max_energy * self.beat_boost)

        # Clamp to reasonable range
        ideal_scale = max(WAVE_SCALE_MIN, min(WAVE_SCALE_MAX, ideal_scale))

        # Smoothly adjust (slow lerp to avoid jarring changes)
        self.dynamic_scale = (1 - WAVE_SCALE_SMOOTH_ALPHA) * self.dynamic_scale + WAVE_SCALE_SMOOTH_ALPHA * ideal_scale

    def render(self, screen, frame_data, neighbor_brightness=1.0):
        """
        Render wave visualization for this rank's quadrant.

        Args:
            screen: pygame Surface to render to
            frame_data: dict containing:
                - 'bands': full mel band array (96 values)
                - 'beat': beat flag
                - 'scene': scene index
                - 'palette': palette index
            neighbor_brightness: brightness multiplier from neighbor coupling
        """
        # Extract parameters
        bands = frame_data['bands'].copy()
        beat = frame_data['beat']
        scene = frame_data['scene']
        palette_idx = frame_data['palette']

        # Update beat effects
        if beat:
            self.beat_boost = BEAT_BOOST
            self.beat_glow = 1.0
        else:
            self.beat_boost = max(1.0, self.beat_boost * BEAT_DECAY)
            self.beat_glow = max(0.0, self.beat_glow * BEAT_DECAY)

        # Apply temporal smoothing (attack/decay) for smooth motion
        bands = self._smooth_bands(bands)

        # Apply horizontal smoothing to reduce pointiness
        bands = self._horizontal_smooth(bands)

        # Apply neighbor brightness
        bands = bands * neighbor_brightness

        # Compute dynamic scale factor (auto-adjusts amplitude to fill screen)
        self._compute_dynamic_scale(bands)

        # Fill background
        bg_color = BACKGROUNDS[scene % len(BACKGROUNDS)]
        screen.fill(bg_color)

        # Get palette
        palette = PALETTES[palette_idx % len(PALETTES)]

        # Compute global wave points
        wave_points = self._compute_wave_points(bands)

        # Interpolate for smoother curve
        smooth_points = self._interpolate_points(wave_points)

        # Transform to local screen coordinates
        local_points = self._transform_to_local(smooth_points)

        # Render filled wave polygon
        if len(local_points) >= 2:
            self._render_wave_fill(screen, local_points, palette)

            # Render wave outline
            self._render_wave_line(screen, local_points, palette)

        # Beat flash effect
        if self.beat_glow > 0.1:
            self._render_beat_flash(screen)

    def _compute_wave_points(self, bands):
        """
        Compute global wave points from 96 mel bands.

        Args:
            bands: numpy array of mel band energies (96 values)

        Returns:
            list of (x, amplitude) tuples in global coordinates
        """
        points = []
        x_step = self.total_width / (self.num_points - 1)  # ~20px per band

        for i, energy in enumerate(bands):
            x = i * x_step
            # Amplitude scales with energy, dynamic scale, and beat boost
            amplitude = max(WAVE_MIN_HEIGHT, energy * self.dynamic_scale * self.beat_boost)
            points.append((x, amplitude))

        return points

    def _interpolate_points(self, points):
        """
        Interpolate between wave points for smoother curve.

        Args:
            points: list of (x, amplitude) tuples

        Returns:
            list of interpolated (x, amplitude) tuples
        """
        if len(points) < 2:
            return points

        smooth_points = []
        num_subdivisions = WAVE_SUBDIVISIONS

        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]

            for t in range(num_subdivisions):
                ratio = t / num_subdivisions
                # Simple linear interpolation
                x = x0 + (x1 - x0) * ratio
                y = y0 + (y1 - y0) * ratio
                smooth_points.append((x, y))

        # Add the last point
        smooth_points.append(points[-1])
        return smooth_points

    def _transform_to_local(self, global_points):
        """
        Transform global wave points to local screen coordinates.

        - Clips to this rank's visible region
        - Transforms Y based on row (top grows up, bottom grows down)

        Args:
            global_points: list of (global_x, amplitude) tuples

        Returns:
            list of (local_x, local_y) tuples for pygame rendering
        """
        local_points = []
        margin = 50  # Include points slightly outside for smooth edges

        for gx, amplitude in global_points:
            # Convert global X to local X
            local_x = gx - self.global_x_offset

            # Skip points too far outside this rank's view
            if local_x < -margin or local_x > self.screen_width + margin:
                continue

            # Y transformation based on row
            if self.is_top_row:
                # Wave grows upward from bottom of screen
                local_y = self.screen_height - amplitude
            else:
                # Wave grows downward from top of screen (mirrored)
                local_y = amplitude

            # Clamp Y to screen bounds
            local_y = max(0, min(self.screen_height, local_y))

            local_points.append((local_x, local_y))

        return local_points

    def _render_wave_fill(self, screen, points, palette):
        """
        Render filled area under the wave.

        Args:
            screen: pygame Surface
            points: list of (x, y) tuples (local coordinates)
            palette: list of RGB tuples
        """
        if len(points) < 2:
            return

        fill_color = palette[0]  # Primary color from palette

        # Brighten on beat
        if self.beat_glow > 0.1:
            fill_color = self._brighten_color(fill_color, 1.0 + 0.2 * self.beat_glow)

        # Create polygon: wave points + baseline corners
        polygon_points = list(points)

        if self.is_top_row:
            # Close polygon at bottom of screen
            polygon_points.append((points[-1][0], self.screen_height))
            polygon_points.append((points[0][0], self.screen_height))
        else:
            # Close polygon at top of screen
            polygon_points.append((points[-1][0], 0))
            polygon_points.append((points[0][0], 0))

        # Draw filled polygon
        if len(polygon_points) >= 3:
            pygame.draw.polygon(screen, fill_color, polygon_points)

    def _render_wave_line(self, screen, points, palette):
        """
        Render wave outline.

        Args:
            screen: pygame Surface
            points: list of (x, y) tuples (local coordinates)
            palette: list of RGB tuples
        """
        if len(points) < 2:
            return

        line_color = self._brighten_color(palette[1], 1.3)

        # Brighten further on beat
        if self.beat_glow > 0.1:
            line_color = self._brighten_color(line_color, 1.0 + 0.3 * self.beat_glow)

        # Draw lines connecting all points
        pygame.draw.lines(screen, line_color, False, points, WAVE_LINE_WIDTH)

    def _render_beat_flash(self, screen):
        """
        Render a semi-transparent white flash on beat.

        Args:
            screen: pygame Surface
        """
        flash_alpha = int(self.beat_glow * 40)  # Max 40 alpha
        flash_surface = pygame.Surface((self.screen_width, self.screen_height))
        flash_surface.set_alpha(flash_alpha)
        flash_surface.fill((255, 255, 255))
        screen.blit(flash_surface, (0, 0))

    def _brighten_color(self, color, factor):
        """
        Brighten an RGB color by a factor.

        Args:
            color: (r, g, b) tuple
            factor: brightness multiplier (>1.0 brightens)

        Returns:
            (r, g, b) tuple with values clamped to [0, 255]
        """
        r, g, b = color
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return (r, g, b)


def render_debug_hud(screen, frame_data, rank, font=None, neighbor_data=None):
    """
    Render debug HUD showing frame info.

    Args:
        screen: pygame Surface
        frame_data: dict with 'tick', 't_sec', 'flux', 'beat', etc.
        rank: MPI rank
        font: pygame Font object (optional, creates default if None)
        neighbor_data: dict with 'local_energy', 'neighbors', 'brightness' (optional, Part 2)
    """
    if font is None:
        font = pygame.font.SysFont('monospace', 12)

    # Info text
    tick = frame_data.get('tick', 0)
    t_sec = frame_data.get('t_sec', 0.0)
    flux = frame_data.get('flux', 0.0)
    beat = frame_data.get('beat', False)

    lines = [
        f"Rank: {rank}",
        f"Tick: {tick}",
        f"Time: {t_sec:.2f}s",
        f"Flux: {flux:.3f}",
        f"Beat: {'YES' if beat else 'no'}",
    ]

    # Add neighbor coupling info if available (Part 2)
    if neighbor_data:
        lines.append("")
        lines.append(f"Local E: {neighbor_data.get('local_energy', 0.0):.3f}")
        nbr = neighbor_data.get('neighbors', {})
        lines.append(f"Nbr N: {nbr.get('N', 0.0):.3f}")
        lines.append(f"Nbr S: {nbr.get('S', 0.0):.3f}")
        lines.append(f"Nbr W: {nbr.get('W', 0.0):.3f}")
        lines.append(f"Nbr E: {nbr.get('E', 0.0):.3f}")
        lines.append(f"Bright: {neighbor_data.get('brightness', 1.0):.3f}")

    # Render text
    y_offset = 10
    for line in lines:
        color = (255, 255, 0) if beat else (200, 200, 200)
        text_surface = font.render(line, True, color)
        screen.blit(text_surface, (10, y_offset))
        y_offset += 15


def bars(screen, bands_slice, beat, palette_idx, scene_idx=0, rank=0):
    """
    Simple bar rendering function (for backwards compatibility).

    Args:
        screen: pygame Surface
        bands_slice: numpy array of mel band energies
        beat: bool - beat flag
        palette_idx: int - palette index
        scene_idx: int - scene index
        rank: int - MPI rank
    """
    # Create temporary visualizer
    viz = BarVisualizer(rank, screen.get_width(), screen.get_height())

    # Create frame data dict
    # Need to reconstruct full bands array (pad with zeros)
    full_bands = np.zeros(N_MELS, dtype=np.float32)
    start_idx = rank * BANDS_PER_RANK
    full_bands[start_idx:start_idx + len(bands_slice)] = bands_slice

    frame_data = {
        'bands': full_bands,
        'beat': beat,
        'scene': scene_idx,
        'palette': palette_idx
    }

    viz.render(screen, frame_data)
