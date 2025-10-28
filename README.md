# Music-Driven Multi-Screen Visualization Wall

## Part 1: Base Implementation

A synchronized 4-screen (2x2 grid) music visualization system using MPI for distributed rendering. Rank 0 analyzes audio in real-time and broadcasts visualization data to all ranks.

---

## Project Structure

```
saves/
├── config.py                  # Configuration constants
├── audio.py                   # Audio processing (WAV, STFT, mel, beat detection)
├── visuals.py                 # Rendering functions (bar visualizer)
├── wall.py                    # Main orchestrator (MPI communication)
├── run.sh                     # Execution helper script
├── generate_test_audio.py     # Test audio generation utility
├── assets/                    # Audio files
│   ├── sine_sweep.wav
│   ├── beats_120bpm.wav
│   └── music_test.wav
└── README.md                  # This file
```

---

## Dependencies

### Required Python Packages
```bash
pip install mpi4py numpy pygame
```

### System Requirements
- Python 3.9+
- MPI implementation (OpenMPI or MPICH)
- Display server (X11 for Linux/macOS)
- 4 MPI processes (2x2 grid)

### Audio Requirements
- Mono WAV files
- 44.1 kHz sample rate
- 16-bit PCM format

---

## Setup

### 1. Install Dependencies
```bash
# Install Python packages
pip install mpi4py numpy pygame

# On macOS (if MPI not installed)
brew install open-mpi

# On Linux
sudo apt-get install openmpi-bin libopenmpi-dev
```

### 2. Generate Test Audio
```bash
cd saves/
python3 generate_test_audio.py
```

This creates three test files in `assets/`:
- `sine_sweep.wav` - Logarithmic frequency sweep (good for testing frequency response)
- `beats_120bpm.wav` - Clear beat pattern at 120 BPM (good for testing beat detection)
- `music_test.wav` - Music-like synthesis with bass, melody, and beats (most realistic)

### 3. Convert Your Own Audio (Optional)
```bash
# Convert stereo to mono, 44.1kHz using ffmpeg
ffmpeg -i input.mp3 -ar 44100 -ac 1 output.wav
```

---

## Usage

### Basic Usage
```bash
cd saves/
./run.sh assets/music_test.wav
```

### With Debug HUD
```bash
./run.sh assets/music_test.wav --debug
```

### Direct MPI Command
```bash
mpiexec -n 4 python3 wall.py --audio assets/music_test.wav
```

### For Cluster Deployment
```bash
# Create machine file (4 hosts)
echo "host1" > mach_file
echo "host2" >> mach_file
echo "host3" >> mach_file
echo "host4" >> mach_file

# Run
mpiexec -n 4 -pernode --machinefile mach_file python3 wall.py --audio assets/music_test.wav
```

---

## How It Works

### Architecture

**MPI Communication Pattern** (based on `examples/oneball.py`):
```
Main Loop:
  1. Barrier (synchronize all ranks)
  2. Rank 0: Read audio → STFT → Mel bands → Beat detection → Broadcast
  3. Ranks 1-3: Receive broadcast
  4. All ranks: Render visualization
  5. Display update
  6. Frame rate control (30 FPS)
```

**Window Layout** (based on `examples/images.py`):
```
+------------+------------+
| Rank 0     | Rank 1     |
| (0, 0)     | (960, 0)   |
| Bands 0-23 | Bands 24-47|
+------------+------------+
| Rank 2     | Rank 3     |
| (0, 540)   | (960, 540) |
| Bands 48-71| Bands 72-95|
+------------+------------+
```

### Audio Processing Pipeline (Rank 0 Only)

1. **WAV Reader** (`audio.py:wav_reader`)
   - Loads mono 44.1kHz WAV file
   - Validates format
   - Returns normalized float32 samples

2. **STFT Frame Buffer** (`audio.py:STFTFrameBuffer`)
   - Maintains rolling buffer of N_FFT=1024 samples
   - Every HOP=512 samples (~11.6ms):
     - Apply Hann window
     - Compute FFT
     - Apply mel filterbank (96 bands, 20Hz-8kHz)
     - Log compression (log1p)
   - ~86 audio frames/sec, displayed at 30 FPS (~3 audio hops per visual frame)

3. **Beat Detection** (`audio.py:BeatDetector`)
   - Spectral flux method: `flux = sum(max(mel[t] - mel[t-1], 0))`
   - Beat detected when `flux > threshold * (1 + smoothed_flux)`
   - Minimum 5 frames between beats (prevents double-triggering)
   - Every 4th beat: change scene (background color)
   - Every 8th beat: change palette (bar colors)

4. **Broadcast** (`wall.py`)
   - Frame data dict containing:
     - `tick`: frame counter
     - `t_sec`: time in seconds
     - `bands`: mel band energies (float32[96])
     - `flux`: spectral flux value
     - `beat`: beat flag (bool)
     - `scene`: scene index (background)
     - `palette`: palette index (colors)
   - Uses `comm.bcast()` for automatic serialization

### Visualization (All Ranks)

**Bar Visualizer** (`visuals.py:BarVisualizer`)
- Each rank receives full 96 mel bands
- Extracts assigned slice (24 bands per rank)
- Renders frequency bars:
  - Height = mel energy * scale factor
  - Width = screen width / 24 bands
  - Colors from palette (cycles through 4 colors)
  - Beat effects:
    - Height boost (1.5x)
    - Color brightening
    - White flash overlay
- Rendering uses `pygame.draw.rect()` for performance

**Color Palettes** (4 palettes, cycle on beats):
- Purple-Pink (blue violet, deep pink, hot pink, orchid)
- Blue-Cyan (deep sky blue, dodger blue, cyan, turquoise)
- Orange-Red (orange red, dark orange, orange, gold)
- Green-Yellow (lime green, lawn green, green yellow, yellow green)

**Scenes** (4 backgrounds, cycle on beats):
- Dark blue-black
- Dark red-black
- Dark green-black
- Dark yellow-black

---

## Configuration

All constants are in `config.py`:

### Key Parameters
```python
# Grid
GRID_P, GRID_Q = 2, 2  # 2x2 grid (4 ranks)

# Display
WIN_W, WIN_H = 960, 540  # Window size per rank
TARGET_FPS = 30          # Target frame rate

# Audio
SR = 44100          # Sample rate
N_FFT = 1024        # FFT size
HOP = 512           # Hop size (~11.6ms)
N_MELS = 96         # Mel bands

# Beat Detection
BEAT_THRESHOLD = 2.5  # Spectral flux threshold

# Visuals
BAR_SCALE = 300       # Bar height scaling
BEAT_BOOST = 1.5      # Beat height multiplier
```

### Tuning Tips
- **More responsive beats**: Lower `BEAT_THRESHOLD` (try 1.5-2.0)
- **Taller bars**: Increase `BAR_SCALE` (try 400-500)
- **Stronger beat effects**: Increase `BEAT_BOOST` (try 2.0)
- **Smoother visuals**: Lower `TARGET_FPS` (try 24)
- **More frequency detail**: Increase `N_MELS` (try 128, update `BANDS_PER_RANK`)

---

## Testing

### Test 1: Frequency Response (Sine Sweep)
```bash
./run.sh assets/sine_sweep.wav --debug
```
**Expected**: Bars should move from left (low freq) to right (high freq) smoothly.

### Test 2: Beat Detection
```bash
./run.sh assets/beats_120bpm.wav --debug
```
**Expected**:
- "Beat: YES" appears in debug HUD at ~120 BPM rhythm
- Bars flash/boost on each beat
- Scene/palette changes periodically

### Test 3: Music-Like Content
```bash
./run.sh assets/music_test.wav --debug
```
**Expected**:
- Multiple frequency bands active simultaneously
- Dynamic beat response
- Smooth palette transitions

---

## Troubleshooting

### Issue: ModuleNotFoundError
```
Solution: Install dependencies
pip install mpi4py numpy pygame
```

### Issue: "WAV must be mono"
```
Solution: Convert to mono using ffmpeg
ffmpeg -i input.wav -ac 1 output.wav
```

### Issue: "WAV must be 44100Hz"
```
Solution: Resample using ffmpeg
ffmpeg -i input.wav -ar 44100 output.wav
```

### Issue: Windows not appearing
```
Solution: Check display environment
export DISPLAY=:0
```

### Issue: Windows overlapping incorrectly
```
Solution: Adjust WINDOW_POSITIONS in config.py
based on your display resolution
```

### Issue: Low FPS / stuttering
```
Solutions:
1. Use Ethernet instead of WiFi (for cluster)
2. Lower TARGET_FPS in config.py
3. Reduce N_MELS (fewer frequency bands)
4. Check MPI network performance
```

### Issue: No beat detection
```
Solutions:
1. Lower BEAT_THRESHOLD in config.py (try 1.5)
2. Check audio has transients (use beats_120bpm.wav)
3. Enable --debug to see flux values
```

---

## Performance Notes

### Frame Rate
- **Target**: 30 FPS (33ms per frame)
- **Audio processing**: ~86 analysis frames/sec (11.6ms per hop)
- **Visual updates**: Average 3 audio hops per visual frame
- **Bottleneck**: MPI broadcast + pygame rendering

### Network Requirements (Cluster)
- **Broadcast size**: ~400 bytes per frame (mel bands + metadata)
- **Bandwidth**: ~12 KB/s at 30 FPS (negligible)
- **Latency sensitive**: Use Ethernet, not WiFi
- **Synchronization**: Barrier ensures all ranks stay synchronized

### CPU Usage
- **Rank 0**: Higher (audio processing + FFT)
- **Ranks 1-3**: Lower (rendering only)
- **Typical**: 10-30% per rank on modern hardware

---

## Implementation Notes

### MPI Patterns Used

From `examples/oneball.py`:
- Barrier synchronization at frame start
- Rank 0 orchestrates, others follow
- Broadcast for state distribution
- Clock.tick() for frame rate control

From `examples/images.py`:
- SDL_VIDEO_WINDOW_POS for window positioning
- 2x2 grid layout with rank-based offsets
- Borderless windows (pygame.NOFRAME)

From `examples/bcast.py`:
- mpi4py automatic serialization of Python objects/numpy arrays
- All ranks must call bcast() in same order

### Design Decisions

1. **Why broadcast instead of scatter?**
   - All ranks need same metadata (beat, scene, palette)
   - Each rank extracts its own band slice locally
   - Simpler than per-rank data packing

2. **Why 30 FPS instead of 60?**
   - Reduces MPI communication overhead
   - Audio analysis is ~86 FPS anyway (oversampled)
   - 30 FPS sufficient for smooth visualization

3. **Why spectral flux for beats?**
   - Simple and effective
   - No training required
   - Low computational cost
   - Works well with mel bands

4. **Why bars instead of other visuals?**
   - Simple to render (pygame.draw.rect)
   - Clear frequency representation
   - Scales well across ranks
   - Easy to extend (Part 2)

---

## Next Steps (Part 2 Preview)

Part 2 will add **neighbor coupling** using MPI Cartesian topology:
- Create 2x2 Cartesian communicator
- Exchange energy values with adjacent ranks (N, S, E, W)
- Modulate brightness based on neighbor activity
- Add flow effects (directional influence)
- Implement beat-wave ripples across tiles

Stay tuned!

---

## References

- Design document: `saves/design_doc.md`
- Example implementations: `examples/oneball.py`, `examples/images.py`
- MPI documentation: https://mpi4py.readthedocs.io/
- Pygame documentation: https://www.pygame.org/docs/

---

**Author**: Implemented using MPI patterns from vis141a examples
**Date**: 2025-10-28
**Course**: VIS 141A - Visual Arts with MPI
