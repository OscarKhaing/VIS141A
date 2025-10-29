# Music Visualization - Quick Start Guide

## visualize.py - All-in-One Script

The `visualize.py` script automatically handles everything:
- Auto-detects audio format (MP3 or WAV)
- Converts MP3 to WAV if needed
- Validates WAV format
- Launches synchronized 4-screen visualization
- Cleans up temporary files

### Basic Usage

```bash
# Activate virtual environment
source ../venv/bin/activate

# Run with WAV file
mpiexec -n 4 python3 visualize.py assets/sine_sweep.wav

# Run with MP3 file (auto-converts)
mpiexec -n 4 python3 visualize.py assets/lone_digger.mp3

# With debug HUD
mpiexec -n 4 python3 visualize.py assets/music_test.wav --debug

# Keep converted files (don't auto-delete)
mpiexec -n 4 python3 visualize.py song.mp3 --keep-converted
```

### How It Works

1. **Auto-Detection**: Determines if input is MP3 or WAV
2. **Conversion** (if needed): Converts MP3 to mono 44.1kHz WAV
3. **Validation**: Ensures WAV is correct format
4. **Visualization**: Launches MPI visualization with 4 processes
5. **Cleanup**: Removes temporary converted files (unless --keep-converted)

### Supported Formats

**Input:**
- MP3 files (.mp3)
- WAV files (.wav) - must be mono, 44.1kHz

**Output (if conversion needed):**
- Mono WAV
- 44.1kHz sample rate
- 16-bit PCM

### Controls

- **ESC** or **Q**: Quit visualization
- **Ctrl+C**: Force quit (all ranks)

### Options

```
positional arguments:
  audio_file        Path to audio file (MP3 or WAV)

optional arguments:
  -h, --help        show this help message and exit
  --debug           Show debug HUD with frame info
  --keep-converted  Keep converted WAV files (don't delete temporary files)
```

---

## Original Scripts (for testing)

### wall.py - Core MPI Visualization

Direct visualization without auto-conversion:

```bash
mpiexec -n 4 python3 wall.py --audio assets/sine_sweep.wav
mpiexec -n 4 python3 wall.py --audio assets/sine_sweep.wav --debug
```

### convert_mp3_to_wav.py - Manual Conversion

Convert MP3 to WAV manually:

```bash
python3 convert_mp3_to_wav.py input.mp3
python3 convert_mp3_to_wav.py input.mp3 output.wav
```

### generate_test_audio.py - Create Test Files

Generate synthetic test audio:

```bash
python3 generate_test_audio.py
# Creates: sine_sweep.wav, beats_120bpm.wav, music_test.wav
```

---

## Examples

### Example 1: Quick Test (Sine Sweep)
```bash
mpiexec -n 4 python3 visualize.py assets/sine_sweep.wav
```
10 second frequency sweep, good for testing frequency response.

### Example 2: Beat Detection Test
```bash
mpiexec -n 4 python3 visualize.py assets/beats_120bpm.wav --debug
```
15 seconds with clear 120 BPM beats, watch for "Beat: YES" in HUD.

### Example 3: Real Music (MP3)
```bash
mpiexec -n 4 python3 visualize.py assets/lone_digger.mp3
```
Full song (3m 50s), auto-converts from MP3, great for demo.

### Example 4: Your Own Music
```bash
# Works with any MP3 or WAV!
mpiexec -n 4 python3 visualize.py /path/to/your/song.mp3
```

---

## Troubleshooting

### Issue: "This program requires 4 MPI processes"
**Solution:** Always run with `mpiexec -n 4`

### Issue: "cannot load MPI library"
**Solution:** Use `mpiexec` to run, don't run Python directly
```bash
# ✗ Wrong
python3 visualize.py song.mp3

# ✓ Correct
mpiexec -n 4 python3 visualize.py song.mp3
```

### Issue: "WAV must be mono"
**Solution:** Let visualize.py auto-convert, or use convert_mp3_to_wav.py

### Issue: Windows not appearing
**Solution:**
```bash
export DISPLAY=:0
mpiexec -n 4 python3 visualize.py song.mp3
```

### Issue: Low FPS
**Solution:**
1. Use simpler audio (shorter duration)
2. Lower TARGET_FPS in config.py
3. Use Ethernet instead of WiFi (for cluster)

---

## File Locations

```
saves/
├── visualize.py                # ← Main all-in-one script
├── wall.py                     # Original MPI visualizer
├── convert_mp3_to_wav.py       # Manual converter
├── generate_test_audio.py      # Test audio generator
├── test_visualize_logic.py     # Unit tests
├── audio.py                    # Audio processing
├── visuals.py                  # Rendering
├── config.py                   # Configuration
└── assets/                     # Audio files
    ├── sine_sweep.wav
    ├── beats_120bpm.wav
    ├── music_test.wav
    └── lone_digger.{mp3,wav}
```

---

## Pro Tips

1. **Use --debug for first run** to see what's happening
2. **Test with short files first** (sine_sweep.wav) before long songs
3. **MP3 conversion takes ~5 seconds** for typical songs
4. **Converted files go to /tmp** and are auto-deleted
5. **Use --keep-converted** if you want to reuse converted files
6. **Press ESC or Q** to quit cleanly (don't Ctrl+C unless necessary)

---

## Quick Reference

| Task | Command |
|------|---------|
| Run with WAV | `mpiexec -n 4 python3 visualize.py file.wav` |
| Run with MP3 | `mpiexec -n 4 python3 visualize.py file.mp3` |
| Debug mode | Add `--debug` flag |
| Keep converted | Add `--keep-converted` flag |
| Manual convert | `python3 convert_mp3_to_wav.py file.mp3` |
| Generate tests | `python3 generate_test_audio.py` |

---

**Ready to visualize!** 🎵🎨
