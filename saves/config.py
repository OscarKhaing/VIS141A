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
# Frequency Range Configuration
# ============================================================================
FMIN = 20.0      # Minimum frequency (Hz)
FMAX = 8000.0    # Maximum frequency (Hz)

# ============================================================================
# Data Types
# ============================================================================
DTYPE_FLOAT = 'float32'
DTYPE_UINT8 = 'uint8'
DTYPE_INT32 = 'int32'
