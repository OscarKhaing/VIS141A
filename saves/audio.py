"""
Audio processing module for music-driven visualization.
Includes WAV reading, STFT, mel filterbank, and beat detection.
Part 1: Base Implementation
"""

import numpy as np
import wave
from config import *


def wav_reader(filepath):
    """
    Read a WAV file and return audio samples.

    Args:
        filepath: Path to WAV file (must be mono, 44.1kHz)

    Returns:
        numpy array of float32 samples normalized to [-1, 1]

    Raises:
        AssertionError if WAV is not mono 44.1kHz
    """
    with wave.open(filepath, 'rb') as wf:
        # Validate format
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        assert n_channels == 1, f"WAV must be mono (got {n_channels} channels)"
        assert framerate == SR, f"WAV must be {SR}Hz (got {framerate}Hz)"

        # Read all frames
        raw_data = wf.readframes(n_frames)

        # Convert to numpy array based on sample width
        if sample_width == 1:  # 8-bit
            audio = np.frombuffer(raw_data, dtype=np.uint8)
            audio = (audio.astype(np.float32) - 128) / 128.0
        elif sample_width == 2:  # 16-bit
            audio = np.frombuffer(raw_data, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
        elif sample_width == 4:  # 32-bit
            audio = np.frombuffer(raw_data, dtype=np.int32)
            audio = audio.astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width} bytes")

        return audio


def make_mel_filterbank(sr=SR, n_fft=N_FFT, n_mels=N_MELS, fmin=FMIN, fmax=FMAX):
    """
    Create a mel filterbank matrix.

    Args:
        sr: Sample rate (Hz)
        n_fft: FFT size
        n_mels: Number of mel bands
        fmin: Minimum frequency (Hz)
        fmax: Maximum frequency (Hz)

    Returns:
        numpy array of shape (n_mels, n_fft//2 + 1) - mel filterbank matrix
    """
    # Helper: Hz to Mel
    def hz_to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    # Helper: Mel to Hz
    def mel_to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    # Frequency bins
    n_bins = n_fft // 2 + 1
    fft_freqs = np.linspace(0, sr / 2, n_bins)

    # Mel scale points
    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = mel_to_hz(mel_points)

    # Convert Hz points to FFT bin indices
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    # Create filterbank
    filterbank = np.zeros((n_mels, n_bins), dtype=np.float32)

    for m in range(n_mels):
        left = bin_points[m]
        center = bin_points[m + 1]
        right = bin_points[m + 2]

        # Rising slope
        for k in range(left, center):
            if center > left:
                filterbank[m, k] = (k - left) / (center - left)

        # Falling slope
        for k in range(center, right):
            if right > center:
                filterbank[m, k] = (right - k) / (right - center)

    return filterbank


class STFTFrameBuffer:
    """
    Maintains a rolling buffer for STFT computation.
    Processes audio in hops and returns mel spectrogram frames.
    """

    def __init__(self, n_fft=N_FFT, hop=HOP, sr=SR, n_mels=N_MELS):
        """
        Initialize STFT frame buffer.

        Args:
            n_fft: FFT size
            hop: Hop size (samples)
            sr: Sample rate
            n_mels: Number of mel bands
        """
        self.n_fft = n_fft
        self.hop = hop
        self.sr = sr
        self.n_mels = n_mels

        # Rolling buffer
        self.buffer = np.zeros(n_fft, dtype=np.float32)

        # Hann window
        self.window = np.hanning(n_fft).astype(np.float32)

        # Mel filterbank
        self.mel_fb = make_mel_filterbank(sr, n_fft, n_mels)

        # Previous mel bands (for spectral flux)
        self.prev_mel = np.zeros(n_mels, dtype=np.float32)

    def process_hop(self, audio_hop):
        """
        Process one hop of audio and return mel bands.

        Args:
            audio_hop: numpy array of length HOP (new samples)

        Returns:
            numpy array of length N_MELS (mel band energies)
        """
        assert len(audio_hop) == self.hop, f"Hop must be {self.hop} samples"

        # Shift buffer and append new samples
        self.buffer[:-self.hop] = self.buffer[self.hop:]
        self.buffer[-self.hop:] = audio_hop

        # Apply window
        windowed = self.buffer * self.window

        # FFT
        fft_result = np.fft.rfft(windowed)
        magnitude = np.abs(fft_result).astype(np.float32)

        # Apply mel filterbank
        mel_bands = np.dot(self.mel_fb, magnitude)

        # Log compression (log1p = log(1 + x))
        mel_bands = np.log1p(mel_bands)

        return mel_bands


class BeatDetector:
    """
    Detects beats using spectral flux method.
    """

    def __init__(self, threshold=BEAT_THRESHOLD, smoothing=FLUX_SMOOTHING):
        """
        Initialize beat detector.

        Args:
            threshold: Spectral flux threshold for beat detection
            smoothing: Smoothing factor for flux history
        """
        self.threshold = threshold
        self.smoothing = smoothing

        # Previous mel bands
        self.prev_mel = None

        # Smoothed flux history
        self.flux_smooth = 0.0

        # Beat state
        self.beat_active = False
        self.frames_since_beat = 0
        self.min_beat_interval = 5  # Minimum frames between beats

    def process(self, mel_bands):
        """
        Process mel bands and detect beats.

        Args:
            mel_bands: numpy array of mel band energies

        Returns:
            tuple (flux, beat_flag)
                flux: float - spectral flux value
                beat_flag: bool - True if beat detected
        """
        if self.prev_mel is None:
            self.prev_mel = mel_bands.copy()
            return 0.0, False

        # Compute spectral flux (sum of positive differences)
        diff = mel_bands - self.prev_mel
        flux = np.sum(np.maximum(diff, 0.0))

        # Update smoothed flux
        self.flux_smooth = (1.0 - self.smoothing) * self.flux_smooth + self.smoothing * flux

        # Beat detection
        beat = False
        if self.frames_since_beat >= self.min_beat_interval:
            if flux > self.threshold * (1.0 + self.flux_smooth):
                beat = True
                self.frames_since_beat = 0

        # Update state
        self.prev_mel = mel_bands.copy()
        self.frames_since_beat += 1

        return flux, beat


class AudioStream:
    """
    Combines all audio processing components for easy use.
    """

    def __init__(self, filepath):
        """
        Initialize audio stream.

        Args:
            filepath: Path to WAV file
        """
        # Load audio
        self.audio = wav_reader(filepath)
        self.total_samples = len(self.audio)
        self.current_pos = 0

        # Initialize processors
        self.stft = STFTFrameBuffer()
        self.beat_detector = BeatDetector()

        # State
        self.tick = 0
        self.scene = 0
        self.palette = 0
        self.beat_counter = 0

    def get_next_frame(self):
        """
        Get next audio analysis frame (with frame skipping for performance).

        Processes one hop and skips ahead by HOPS_PER_FRAME to reduce frame count
        by ~3x while maintaining visual quality.

        Returns:
            dict with keys:
                'tick': frame counter
                't_sec': time in seconds
                'bands': mel band energies (float32[N_MELS])
                'flux': spectral flux value
                'beat': beat flag (bool)
                'scene': scene index
                'palette': palette index
                'eos': end of stream flag
        """
        # Check if we've reached end of audio
        if self.current_pos + HOP > self.total_samples:
            return {
                'tick': self.tick,
                't_sec': self.current_pos / SR,
                'bands': np.zeros(N_MELS, dtype=np.float32),
                'flux': 0.0,
                'beat': False,
                'scene': self.scene,
                'palette': self.palette,
                'eos': True
            }

        # Process one hop
        audio_hop = self.audio[self.current_pos:self.current_pos + HOP]
        mel_bands = self.stft.process_hop(audio_hop)
        flux, beat = self.beat_detector.process(mel_bands)

        # Skip ahead by HOPS_PER_FRAME to reduce frame count (~3x speedup)
        self.current_pos += HOP * HOPS_PER_FRAME

        # Update scene/palette on strong beats
        if beat:
            self.beat_counter += 1
            if self.beat_counter % 4 == 0:  # Every 4th beat
                self.scene = (self.scene + 1) % len(BACKGROUNDS)
            if self.beat_counter % 8 == 0:  # Every 8th beat
                self.palette = (self.palette + 1) % len(PALETTES)

        # Increment tick
        self.tick += 1

        return {
            'tick': self.tick,
            't_sec': self.current_pos / SR,
            'bands': mel_bands,
            'flux': flux,
            'beat': beat,
            'scene': self.scene,
            'palette': self.palette,
            'eos': False
        }
