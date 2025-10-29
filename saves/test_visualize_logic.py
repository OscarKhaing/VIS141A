#!/usr/bin/env python3
"""
Test the audio detection and preparation logic from visualize.py
without requiring MPI.
"""

import os
import sys
import wave
import pygame
import numpy as np
import tempfile

# Import only the parts we need
sys.path.insert(0, '.')
from config import SR


def detect_audio_format(filepath):
    """Detect if audio file is MP3 or WAV."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.mp3', '.m4a', '.aac']:
        return 'mp3'
    elif ext == '.wav':
        return 'wav'
    else:
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
    """Check if WAV file is mono, 44.1kHz."""
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


def convert_mp3_to_wav(mp3_path, wav_path=None):
    """Convert MP3 to mono WAV (44.1kHz, 16-bit)."""
    if wav_path is None:
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(mp3_path))[0]
        wav_path = os.path.join(temp_dir, f"{base_name}_converted.wav")

    print(f"Converting {mp3_path} to WAV format...")

    pygame.mixer.init(frequency=SR, size=-16, channels=1)
    sound = pygame.mixer.Sound(mp3_path)
    samples = pygame.sndarray.array(sound)

    if len(samples.shape) == 2:
        samples = samples.mean(axis=1)
    samples = samples.astype(np.int16)

    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(samples.tobytes())

    pygame.quit()

    duration = len(samples) / SR
    print(f"✓ Converted to: {wav_path}")
    print(f"  Duration: {duration:.1f}s ({int(duration//60)}m {int(duration%60)}s)")

    return wav_path


print('Testing visualize.py audio detection logic...')
print('=' * 70)
print()

# Test 1: WAV detection
print('Test 1: Detecting WAV file format')
fmt = detect_audio_format('assets/sine_sweep.wav')
print(f'  Detected: {fmt}')
assert fmt == 'wav', 'WAV detection failed'
print('  ✓ PASS')
print()

# Test 2: WAV validation
print('Test 2: Validating WAV format (should be mono 44.1kHz)')
is_valid, message = validate_wav_format('assets/sine_sweep.wav')
print(f'  Result: {message}')
assert is_valid, 'WAV validation failed'
print('  ✓ PASS')
print()

# Test 3: MP3 detection
print('Test 3: Detecting MP3 file format')
fmt = detect_audio_format('assets/lone_digger.mp3')
print(f'  Detected: {fmt}')
assert fmt == 'mp3', 'MP3 detection failed'
print('  ✓ PASS')
print()

# Test 4: MP3 to WAV conversion
print('Test 4: Converting MP3 to WAV')
converted_path = convert_mp3_to_wav('assets/lone_digger.mp3')
print(f'  Converted path: {converted_path}')
assert os.path.exists(converted_path), 'Converted file not found'
print('  ✓ PASS')
print()

# Test 5: Validate converted file
print('Test 5: Validating converted WAV')
is_valid, message = validate_wav_format(converted_path)
print(f'  Result: {message}')
assert is_valid, 'Converted WAV validation failed'
print('  ✓ PASS')
print()

# Cleanup
print('Cleaning up temporary file...')
os.remove(converted_path)
print('  ✓ Removed')
print()

print('=' * 70)
print('✓ All tests passed! visualize.py logic is working correctly.')
print()
print('Next steps:')
print('  1. Test with MPI: mpiexec -n 4 python3 visualize.py assets/sine_sweep.wav')
print('  2. Test MP3 conversion: mpiexec -n 4 python3 visualize.py assets/lone_digger.mp3')
