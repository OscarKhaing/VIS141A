"""
Configuration constants for music-driven multi-screen visualization.
Part 1: Base Implementation
"""

# ============================================================================
# MPI Grid Configuration
# ============================================================================
GRID_P = 2  # Grid rows
GRID_Q = 2  # Grid columns
TOTAL_RANKS = GRID_P * GRID_Q  # Should be 4

# ============================================================================
# Display Configuration
# ============================================================================
WIN_W = 960   # Window width per rank (pixels)
WIN_H = 540   # Window height per rank (pixels)
TARGET_FPS = 30  # Target frames per second

# Window positions for 2x2 grid (rank -> (x, y))
WINDOW_POSITIONS = {
    0: (0, 0),           # Top-left
    1: (WIN_W, 0),       # Top-right
    2: (0, WIN_H),       # Bottom-left
    3: (WIN_W, WIN_H)    # Bottom-right
}

# ============================================================================
# Audio Configuration
# ============================================================================
SR = 44100        # Sample rate (Hz)
N_FFT = 1024      # FFT size
HOP = 512         # Hop size (samples)
N_MELS = 96       # Number of mel bands

# Derived audio parameters
HOP_DURATION = HOP / SR  # ~11.6ms per hop
HOPS_PER_SEC = SR / HOP  # ~86 hops/sec
HOPS_PER_FRAME = int(HOPS_PER_SEC / TARGET_FPS)  # ~3 hops per visual frame

# ============================================================================
# Beat Detection Configuration
# ============================================================================
BEAT_THRESHOLD = 2.5  # Spectral flux threshold for beat detection
FLUX_SMOOTHING = 0.1  # Smoothing factor for flux computation

# ============================================================================
# Visualization Configuration
# ============================================================================
# Number of bands per rank
BANDS_PER_RANK = N_MELS // TOTAL_RANKS  # 24 bands per rank

# Color palettes (RGB tuples)
PALETTES = [
    # Palette 0: Purple-Pink
    [
        (138, 43, 226),   # Blue Violet
        (255, 20, 147),   # Deep Pink
        (255, 105, 180),  # Hot Pink
        (186, 85, 211),   # Medium Orchid
    ],
    # Palette 1: Blue-Cyan
    [
        (0, 191, 255),    # Deep Sky Blue
        (30, 144, 255),   # Dodger Blue
        (0, 255, 255),    # Cyan
        (64, 224, 208),   # Turquoise
    ],
    # Palette 2: Orange-Red
    [
        (255, 69, 0),     # Orange Red
        (255, 140, 0),    # Dark Orange
        (255, 165, 0),    # Orange
        (255, 215, 0),    # Gold
    ],
    # Palette 3: Green-Yellow
    [
        (50, 205, 50),    # Lime Green
        (124, 252, 0),    # Lawn Green
        (173, 255, 47),   # Green Yellow
        (154, 205, 50),   # Yellow Green
    ],
]

# Background colors for different scenes
BACKGROUNDS = [
    (10, 10, 20),   # Dark blue-black
    (20, 10, 10),   # Dark red-black
    (10, 20, 10),   # Dark green-black
    (20, 20, 10),   # Dark yellow-black
]

# Bar rendering parameters
BAR_SPACING = 2       # Pixels between bars
BAR_MIN_HEIGHT = 10   # Minimum bar height (pixels)
BAR_SCALE = 300       # Scaling factor for mel band to pixel height
BEAT_BOOST = 1.5      # Multiplier for bar height on beat
BEAT_DECAY = 0.9      # Decay rate for beat effect

# ============================================================================
# Band Smoothing Configuration (Attack/Decay)
# ============================================================================
# Creates smooth, professional motion: fast attack (responsive), slow decay (peaks hang)
ATTACK_ALPHA = 0.6    # Fast attack: higher = faster response to increases (0-1)
DECAY_ALPHA = 0.15    # Slow decay: lower = slower fall-off, peaks linger (0-1)

# ============================================================================
# Part 3: Wave Visualization Configuration
# ============================================================================
WAVE_SCALE = 100          # Amplitude scaling factor (energy -> pixels)
WAVE_MIN_HEIGHT = 5       # Minimum wave displacement (pixels)
WAVE_SUBDIVISIONS = 4     # Interpolation smoothness (points between bands)
WAVE_LINE_WIDTH = 3       # Wave outline thickness (pixels)

# Horizontal smoothing: reduces pointiness by blurring adjacent band values
# Options: 3-point (responsive), 5-point (smoother), 7-point (very smooth)
WAVE_SMOOTH_KERNEL_3 = [0.25, 0.5, 0.25]                    # 3-point: light smoothing
WAVE_SMOOTH_KERNEL_5 = [0.0625, 0.25, 0.375, 0.25, 0.0625]  # 5-point: [1,4,6,4,1]/16
WAVE_SMOOTH_PASSES = 2    # Number of smoothing passes (1-3, more = rounder)

# Dynamic amplitude scaling: auto-adjusts so max peak reaches target height
WAVE_TARGET_HEIGHT_RATIO = 0.45   # Target: max peak at 45% of screen height
WAVE_SCALE_SMOOTH_ALPHA = 0.05    # Slow adjustment to avoid jarring changes (0-1)
WAVE_SCALE_MIN = 50               # Minimum scale factor (prevents over-amplification)
WAVE_SCALE_MAX = 500              # Maximum scale factor (prevents clipping)

# ============================================================================
# Frequency Range Configuration
# ============================================================================
FMIN = 20.0      # Minimum frequency (Hz)
FMAX = 8000.0    # Maximum frequency (Hz)

# ============================================================================
# Part 2: Neighbor Coupling Configuration
# ============================================================================
NEIGHBOR_COUPLING_ALPHA = 0.2   # Smoothing factor for neighbor energy (0-1)
NEIGHBOR_COUPLING_K = 0.6       # Coupling strength multiplier
NEIGHBOR_BASE_BRIGHTNESS = 0.9  # Base brightness when using neighbor coupling

# ============================================================================
# Part 4: 3D Ribbon Wave Configuration
# ============================================================================
# Each audio frame becomes a "ribbon slice" traveling along a diagonal path
# from near (bottom-left) to far (middle-right), creating depth illusion.

RIBBON_NUM_SLICES = 45         # Number of historical frames to display (more = better fade)
RIBBON_SLICE_SPEED = 0.02      # How fast slices move along path (t increment per frame)
RIBBON_SLICE_WIDTH = 1.2       # Width of each slice in world units

# 3D Path endpoints (normalized coordinates: x, y, z)
RIBBON_PATH_START = (-0.8, -0.3, 0.5)   # Near, bottom-left
RIBBON_PATH_END = (1.6, 0.1, 4.0)       # Far, further right with more depth

# Depth fading (creates sense of distance)
RIBBON_NEAR_ALPHA = 1.0        # Opacity at near (full)
RIBBON_FAR_ALPHA = 0.2         # Opacity at far (faded)
RIBBON_NEAR_AMPLITUDE = 1.0    # Wave height multiplier at near
RIBBON_FAR_AMPLITUDE = 0.4     # Wave height multiplier at far

# Line rendering
RIBBON_LINE_WIDTH = 8          # Line thickness for each slice

# ============================================================================
# Data Types
# ============================================================================
DTYPE_FLOAT = 'float32'
DTYPE_UINT8 = 'uint8'
DTYPE_INT32 = 'int32'
