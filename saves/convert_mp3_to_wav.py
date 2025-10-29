#!/usr/bin/env python3
"""
Convert MP3 to mono WAV (44.1kHz, 16-bit) using pygame.
"""

import pygame
import wave
import numpy as np
import sys

if len(sys.argv) < 2:
    print("Usage: python3 convert_mp3_to_wav.py <input.mp3> [output.wav]")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.mp3', '.wav')

print(f"Converting {input_file} to {output_file}...")

# Initialize pygame mixer
pygame.mixer.init(frequency=44100, size=-16, channels=1)

# Load MP3
sound = pygame.mixer.Sound(input_file)

# Get raw audio data
samples = pygame.sndarray.array(sound)
print(f"Original shape: {samples.shape}")

# Convert to mono if stereo
if len(samples.shape) == 2:
    print("Converting stereo to mono...")
    samples = samples.mean(axis=1)

# Convert to int16 if needed
samples = samples.astype(np.int16)

print(f"Final shape: {samples.shape}, dtype: {samples.dtype}")

# Write WAV file
with wave.open(output_file, 'wb') as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(44100)
    wav_file.writeframes(samples.tobytes())

# Verify
with wave.open(output_file, 'rb') as wav_file:
    print(f"\n✓ Created: {output_file}")
    print(f"  Channels: {wav_file.getnchannels()}")
    print(f"  Sample width: {wav_file.getsampwidth()} bytes")
    print(f"  Frame rate: {wav_file.getframerate()} Hz")
    print(f"  Duration: {wav_file.getnframes() / wav_file.getframerate():.2f}s")

pygame.quit()
print("\n✓ Conversion complete!")
