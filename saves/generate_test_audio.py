#!/usr/bin/env python3
"""
Generate test audio files for visualization testing.
Creates synthetic audio with known frequency content.
"""

import numpy as np
import wave
import struct

SR = 44100  # Sample rate


def generate_sine_sweep(duration=10.0, f_start=100, f_end=8000, sr=SR):
    """
    Generate a logarithmic sine sweep.

    Args:
        duration: Duration in seconds
        f_start: Starting frequency (Hz)
        f_end: Ending frequency (Hz)
        sr: Sample rate

    Returns:
        numpy array of float32 samples
    """
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples)

    # Logarithmic frequency sweep
    k = (f_end / f_start) ** (1.0 / duration)
    phase = 2 * np.pi * f_start * duration / np.log(k) * (k ** t - 1)
    audio = np.sin(phase).astype(np.float32)

    # Apply fade in/out to avoid clicks
    fade_samples = int(0.1 * sr)  # 100ms fade
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    audio[:fade_samples] *= fade_in
    audio[-fade_samples:] *= fade_out

    return audio


def generate_beat_pattern(duration=10.0, bpm=120, sr=SR):
    """
    Generate audio with clear beats at specified BPM.

    Args:
        duration: Duration in seconds
        bpm: Beats per minute
        sr: Sample rate

    Returns:
        numpy array of float32 samples
    """
    n_samples = int(duration * sr)
    audio = np.zeros(n_samples, dtype=np.float32)

    # Calculate beat interval
    beat_interval = 60.0 / bpm  # seconds per beat
    beat_samples = int(beat_interval * sr)

    # Generate beats
    beat_duration = 0.05  # 50ms beat
    beat_samples_dur = int(beat_duration * sr)

    for i in range(int(duration / beat_interval)):
        start = i * beat_samples
        end = start + beat_samples_dur
        if end < n_samples:
            # Create beat (mix of frequencies)
            t = np.arange(beat_samples_dur) / sr
            beat = (
                0.5 * np.sin(2 * np.pi * 100 * t) +  # Bass
                0.3 * np.sin(2 * np.pi * 200 * t) +  # Mid
                0.2 * np.sin(2 * np.pi * 4000 * t)   # High click
            )
            # Envelope
            env = np.exp(-10 * t)
            beat *= env
            audio[start:end] = beat

    # Normalize
    audio /= np.max(np.abs(audio))

    return audio


def generate_music_like(duration=30.0, sr=SR):
    """
    Generate more music-like test audio with bass, melody, and beats.

    Args:
        duration: Duration in seconds
        sr: Sample rate

    Returns:
        numpy array of float32 samples
    """
    n_samples = int(duration * sr)
    t = np.linspace(0, duration, n_samples)

    # Bass line (low frequency oscillation)
    bass_freq = 2.0  # 2 Hz modulation of 100 Hz
    bass = 0.4 * np.sin(2 * np.pi * 100 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * bass_freq * t))

    # Melody (higher frequencies)
    melody_freq = 440  # A4
    melody_mod = 0.5  # Slow vibrato
    melody = 0.3 * np.sin(2 * np.pi * melody_freq * t * (1 + 0.02 * np.sin(2 * np.pi * melody_mod * t)))

    # Harmony
    harmony = 0.2 * np.sin(2 * np.pi * 554.37 * t)  # C#5

    # Percussion (filtered noise bursts)
    percussion = np.zeros(n_samples)
    beat_interval_samples = sr // 2  # 120 BPM
    for i in range(0, n_samples, beat_interval_samples):
        if i + 1000 < n_samples:
            percussion[i:i+1000] = np.random.randn(1000) * np.exp(-np.arange(1000) / 100)

    percussion *= 0.2

    # Combine
    audio = bass + melody + harmony + percussion

    # Normalize
    audio /= np.max(np.abs(audio)) * 1.1  # Leave some headroom
    audio = audio.astype(np.float32)

    return audio


def write_wav(filename, audio, sr=SR):
    """
    Write audio to WAV file (mono, 16-bit).

    Args:
        filename: Output filename
        audio: numpy array of float32 samples [-1, 1]
        sr: Sample rate
    """
    # Convert to 16-bit integer
    audio_int = (audio * 32767).astype(np.int16)

    # Write WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(audio_int.tobytes())

    print(f"Generated: {filename} ({len(audio)/sr:.2f}s)")


if __name__ == '__main__':
    import sys
    import os

    # Create assets directory if it doesn't exist
    assets_dir = 'assets'
    os.makedirs(assets_dir, exist_ok=True)

    # Generate test files
    print("Generating test audio files...")

    # 1. Sine sweep (good for testing frequency response)
    audio = generate_sine_sweep(duration=10.0)
    write_wav(f'{assets_dir}/sine_sweep.wav', audio)

    # 2. Beat pattern (good for testing beat detection)
    audio = generate_beat_pattern(duration=15.0, bpm=120)
    write_wav(f'{assets_dir}/beats_120bpm.wav', audio)

    # 3. Music-like (most realistic test)
    audio = generate_music_like(duration=30.0)
    write_wav(f'{assets_dir}/music_test.wav', audio)

    print("\nTest audio files created in assets/")
    print("Run with: ./run.sh assets/music_test.wav --debug")
