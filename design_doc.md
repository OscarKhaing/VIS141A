# Part 1 — Base Implementation (Music-Driven Multi-Screen Wall)

## 1) Goal & Scope

* Build a synchronized multi-screen visualization where each MPI rank displays one tile.
* Rank 0 reads a local mono 44.1kHz WAV, performs short-time analysis, detects beats, and broadcasts compact frames to all ranks.
* Each rank renders its assigned band slice; strong beats cause global scene/palette changes.

## 2) System Overview

* Rank 0 (Conductor): Read WAV -> STFT/Mel bands -> Spectral Flux -> Beat flag -> Broadcast.
* Ranks 1..N-1 (Renderers): Receive packet -> Map assigned band slice -> Render visuals.
* Audio hop size: 512 samples @ 44.1kHz (~86 analysis frames/sec).
* Visual update target: 30–45 FPS (average 2–3 hops per visual frame).
* Cartesian MPI grid P×Q matching physical screens.

## 3) Dependencies & Environment

* Python 3.9+, mpi4py, numpy, pygame.
* Raspberry Pi 4+ recommended, Ethernet.
* WAV mono, 44.1kHz (preconvert if needed).

```
mpi4py
numpy
pygame
```

## 4) Configuration

```python
GRID_P, GRID_Q = 2, 2
WIN_W, WIN_H = 960, 540
SR = 44100
N_FFT = 1024
HOP = 512
N_MELS = 96
BEAT_THRESHOLD = 2.5
```

## 5) Data & Message Schema

* tick: int32
* t_sec: float32
* bands: float32[N_MELS]
* flux: float32
* beat: uint8
* scene: uint8
* palette: uint8

## 6) Algorithms

* STFT/Mel:

  * Maintain rolling buffer N_FFT samples.
  * Shift buffer, append hop, apply Hann, FFT, mel filterbank, log1p.
* Beat detection:

  * flux = sum(max(mel - prev, 0)).
  * Beat if flux > BEAT_THRESHOLD.
  * On strong beat: increment scene/palette.

## 7) Control Flow

* Rank 0: read audio, compute mel/flux/beat, broadcast, barrier.
* Ranks > 0: receive frame, render slice, barrier.

## 8) Modules

* audio.py: wav_reader(), make_mel_filterbank(), stft_framebuf(), beat_detector().
* visuals.py: bars(screen, bands_slice, beat, palette).
* wall.py: main loop, argparse, broadcasts, rendering.
* config.py: constants.
* run.sh: mpiexec helper.

```bash
mpiexec -n 4 -pernode --machinefile mach_file python3 wall.py --audio assets/track.wav
```

## 9) Rendering Strategy

* Use primitives (rects/lines) or surfarray blits.
* Avoid per-pixel loops.
* Cache geometry.

## 10) Testing

* Dry run with synthetic sine sweeps.
* Log tick diffs.
* Manual visual checks.

## 11) Risks

* WAV format errors -> assert mono 44.1k.
* Too many broadcasts -> batch hops.
* Wi-Fi jitter -> use Ethernet.

---

# Part 2 — Neighbor Coupling (Inter-Tile Influence)

## 1) Goal & Scope

* Add local to neighbor influence so tiles react to each other.
* Preserve base broadcast; add lightweight neighbor exchanges each frame.

## 2) Influence Model

* local_energy = mean(local_bands)
* Exchange with up to 4 neighbors (N,S,E,W).
* Use neighbor values to modulate brightness, flow, bar motion.
* Apply decay/smoothing to avoid flicker.

## 3) MPI Pattern

* Use Cart_create((P,Q), periods=(False,False)).
* Get neighbors with cart.Shift().
* Use Sendrecv per neighbor.

## 4) Data Structures

```python
local_energy: float
nbr_energy = {"N":0.0, "S":0.0, "W":0.0, "E":0.0}
nbr_smooth = {"N":0.0, "S":0.0, "W":0.0, "E":0.0}
alpha = 0.2
```

## 5) Coupling Rules

* Brightness: brightness = base * (1 + k * max(nbr_smooth.values()))
* Flow: v = sum(dir_energy * direction_vector)
* Beat-wave: boost=1.0 on beat, decays, shared like energy.

## 6) Control Flow Additions

```python
local_energy = float(local_bands.mean())
send = np.array([local_energy], dtype=np.float32)
for dim, disp, key in [(0,-1,"N"),(0,1,"S"),(1,-1,"W"),(1,1,"E")]:
    src, dst = cart.Shift(dim, disp)
    recv = np.zeros(1, dtype=np.float32)
    if dst != MPI.PROC_NULL and src != MPI.PROC_NULL:
        cart.Sendrecv(sendbuf=send, dest=dst, recvbuf=recv, source=src)
        nbr_smooth[key]=(1-alpha)*nbr_smooth[key]+alpha*recv[0]
brightness=0.9*(1.0+0.6*max(nbr_smooth.values()))
bars(screen, local_bands*brightness, beat, palette)
```

## 7) Performance

* 4 small float32 messages per frame.
* Frequency: every frame or every 2–3 frames.
* Order: broadcast -> Sendrecv -> render.

## 8) Edge Cases

* Missing neighbors: PROC_NULL -> value=0.
* Clamp influence to avoid hot spots.
* Lower alpha if oscillating.

## 9) Observability

* HUD showing E_local and neighbor bars.
* Log per-frame time and max neighbor energy.

## 10) Milestones

* C1: print neighbor values.
* C2: smooth + brightness modulation.
* C3: flow vector / beat-wave ripple.
* C4: tune alpha and coupling gains.

## 11) Runbook

* Start with 2x2 grid.
* Confirm low-frequency tile affects adjacent ones.
* If stalls: same Sendrecv order on all ranks.

---

### Deliverables Checklist

* Base Implementation: audio.py, visuals.py, wall.py, config.py, run.sh, WAV asset.
* Neighbor Coupling: Sendrecv logic, smoothing, modulation, HUD (optional).
