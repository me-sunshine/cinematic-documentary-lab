#!/usr/bin/env python3
"""Build the scratch soundtrack and the subtitle file for the animatic.

Everything is synthetic and is a placeholder for the real thing:
  - narration: Piper text-to-speech (voice en_GB-alan-medium), standing in for a narrator
  - music:     plucked-string and bowed-drone synthesis, standing in for the commissioned score
  - ambience:  filtered noise and simple tones, standing in for sound recorded on location

Usage: audio.py <piper voice .onnx> <work dir> <out.wav> <out.srt>
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

from timeline import CUES, ACTS

SR = 48000
DUR = 120.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
T = np.arange(N) / SR


# ------------------------------------------------------------ narration
def tts(voice, text, path, scale):
    subprocess.run(["piper", "-m", voice, "-f", path, "--length-scale", "%.3f" % scale,
                    "--sentence-silence", "0.28"], input=text.encode(), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    nz = np.nonzero(np.abs(x) > 0.004)[0]
    x = x[max(0, nz[0] - 200): nz[-1] + 2000]
    m = int(len(x) * SR / sr)
    return np.interp(np.arange(m) * sr / SR, np.arange(len(x)), x).astype(np.float32)


def narration(voice, work):
    """Place each cue at its start time; speed a cue up slightly if it would run into the next."""
    track = np.zeros(N, np.float32)
    placed = []
    act_end = lambda t: next(e for _, s, e in ACTS if s <= t < e)
    prev_end = 0.0
    for i, (start, text, spoken) in enumerate(CUES):
        start = prev_end + 1.0 if start is None else max(start, prev_end + 0.3)
        nxt = CUES[i + 1][0] if i + 1 < len(CUES) and CUES[i + 1][0] is not None else None
        limit = min(nxt - 0.35 if nxt else 1e9, act_end(start) - 0.3)
        if i + 1 < len(CUES) and CUES[i + 1][0] is None:
            limit -= 2.4                                   # leave room for the beat and the short line after it
        scale = 1.0
        for _ in range(4):
            x = tts(voice, spoken or text, os.path.join(work, "cue%02d.wav" % i), scale)
            d = len(x) / SR
            if start + d <= limit or scale <= 0.86:
                break
            scale = max(0.86, scale * (limit - start) / d * 0.985)
        a = int(start * SR)
        track[a:a + len(x)] += x[: N - a]
        prev_end = start + d
        placed.append(dict(start=round(start, 2), end=round(prev_end, 2), text=text, speed=round(scale, 3),
                           fits=bool(prev_end <= limit + 1e-6)))
    return track / np.max(np.abs(track)) * 0.6, placed


def srt_time(t):
    ms = int(round(t * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def blocks_of(text, limit=84):
    """Split a cue into subtitle blocks at sentence ends, then at a comma or colon near the middle."""
    import re
    out = []
    for sent in re.split(r"(?<=[.?!])\s+", text):
        parts = [sent]
        while any(len(p) > limit for p in parts):
            i = max(range(len(parts)), key=lambda k: len(parts[k]))
            p = parts[i]
            cuts = [m.end() for m in re.finditer(r"[,:]\s", p)] or [p.rfind(" ", 0, len(p) // 2) + 1]
            c = min(cuts, key=lambda c: abs(c - len(p) / 2))
            parts[i:i + 1] = [p[:c].strip(), p[c:].strip()]
        for p in parts:
            if out and len(out[-1]) + 1 + len(p) <= limit and len(p) < 30:
                out[-1] += " " + p
            else:
                out.append(p)
    return out


def two_lines(block, width=42):
    if len(block) <= width:
        return block
    mid = min((i for i, ch in enumerate(block) if ch == " "), key=lambda i: abs(i - len(block) / 2))
    return block[:mid] + "\n" + block[mid + 1:]


def write_srt(placed, path):
    """At most two lines of about 42 characters; a long cue is timed in proportion to block length."""
    out, k = [], 1
    for c in placed:
        blocks = blocks_of(c["text"])
        total = sum(len(b) for b in blocks)
        t = c["start"]
        for b in blocks:
            d = (c["end"] - c["start"]) * len(b) / total
            out.append("%d\n%s --> %s\n%s\n" % (k, srt_time(t), srt_time(t + d), two_lines(b)))
            t += d
            k += 1
    open(path, "w", encoding="utf-8").write("\n".join(out))


# ------------------------------------------------------------ synthesis helpers
def band(lo, hi, seed):
    x = np.random.default_rng(seed).normal(0, 1, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    X = np.fft.rfft(x) * (1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    y = np.fft.irfft(X, N)
    return (y / np.std(y)).astype(np.float32)


def env(t0, t1, fi=0.5, fo=0.5):
    return (np.clip((T - t0) / fi, 0, 1) * np.clip((t1 - T) / fo, 0, 1)).astype(np.float32)


def add(buf, t, x, gain=1.0):
    a = int(t * SR)
    if a >= N:
        return
    x = x[: N - a]
    buf[a:a + len(x)] += x * gain


def mixs(*xs):
    out = np.zeros(max(len(x) for x in xs))
    for x in xs:
        out[: len(x)] += x
    return out


def ping(freqs, decay, dur):
    t = np.arange(int(dur * SR)) / SR
    return sum(np.sin(2 * np.pi * f * t) * a for f, a in freqs) * np.exp(-t / decay)


def burst(lo, hi, dur, decay, seed):
    n = int(dur * SR)
    x = np.random.default_rng(seed).normal(0, 1, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    x = np.fft.irfft(np.fft.rfft(x) * (f > lo) * (f < hi), n)
    return x / (np.std(x) + 1e-9) * np.exp(-np.arange(n) / SR / decay)


def pluck(freq, dur=3.2, bright=0.5, seed=0):
    """Karplus-Strong string, two slightly detuned courses like a Portuguese guitar."""
    out = np.zeros(int(dur * SR), np.float32)
    for k, det in enumerate((1.0, 1.003)):
        n = int(round(SR / (freq * det)))
        buf = np.random.default_rng(seed * 2 + k).uniform(-1, 1, n)
        buf = np.convolve(buf, np.ones(3) / 3, "same") * bright + buf * (1 - bright) * 0.5
        chunks = []
        for _ in range(len(out) // n + 1):
            chunks.append(buf)
            buf = 0.4985 * (buf + np.roll(buf, 1))
        y = np.concatenate(chunks)[: len(out)]
        out += y.astype(np.float32)
    return out / np.max(np.abs(out))


def drone(freq):
    y = np.zeros(N, np.float32)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 0.21 * T + freq)
    ph = 2 * np.pi * freq * np.cumsum(vib) / SR
    for k in range(1, 9):
        y += (np.sin(k * ph + k) / k ** 1.3 * (1 + 0.25 * np.sin(2 * np.pi * (0.07 + 0.013 * k) * T + k))).astype(np.float32)
    return y / np.max(np.abs(y))


D3, D4, E4, F4, FS4, G4, A4, BB4, B4, D5 = 146.83, 293.66, 329.63, 349.23, 369.99, 392.0, 440.0, 466.16, 493.88, 587.33


def soundtrack(vo):
    amb = np.zeros((2, N), np.float32)        # stereo ambience
    fx = np.zeros(N, np.float32)              # spot effects, centre
    mus = np.zeros(N, np.float32)

    # Act 1 and the close: aquarium pump hum
    hum = (0.5 * np.sin(2 * np.pi * 50 * T) + 0.25 * np.sin(2 * np.pi * 100 * T) + 0.1 * np.sin(2 * np.pi * 150 * T)).astype(np.float32)
    e_hum = env(0, 12.6, 1.0, 0.8) + env(113.5, 120, 2.5, 0.9)
    for ch in (0, 1):
        amb[ch] += (hum * 0.05 + band(80, 400, 10 + ch) * 0.035) * e_hum
        # Act 2: wind and heavy water, returning faintly under the archive
        lfo = 0.65 + 0.35 * np.sin(2 * np.pi * 0.13 * T + ch)
        sea = (band(90, 900, 20 + ch) * 0.10 + band(1500, 5000, 22 + ch) * 0.02) * lfo
        amb[ch] += sea * (env(11.7, 22.4, 0.4, 0.8) + 0.3 * env(65.5, 79.2, 1.5, 0.6))
        amb[ch] += band(200, 3000, 30 + ch) * 0.022 * env(21.8, 32.3, 0.6, 0.6)       # the street
        amb[ch] += band(150, 2500, 40 + ch) * 0.02 * env(32, 53, 0.5, 0.5)            # the shop
        amb[ch] += band(60, 600, 50 + ch) * 0.016 * (env(53, 66, 0.8, 1.0) + env(79, 83.2, 0.4, 0.4))   # rooms
        amb[ch] += (np.sin(2 * np.pi * 100 * T) * 0.02 + band(100, 1500, 60 + ch) * 0.03) * env(82.9, 88.2, 0.3, 0.4)  # cold store
        amb[ch] += band(120, 1800, 70 + ch) * 0.018 * env(88, 113.5, 0.6, 2.0)        # kitchen and table

    add(fx, 22.0, ping([(1900, 1), (2850, 0.5)], 0.35, 1.4), 0.07)                    # tram bell, twice
    add(fx, 22.5, ping([(1900, 1), (2850, 0.5)], 0.35, 1.4), 0.05)
    for i in range(44):                                                               # shutter rattle
        add(fx, 25.6 + i * 0.055, burst(700, 5000, 0.05, 0.012, 100 + i), 0.05 * (1 - i / 60))
    for t, g in ((37.15, 0.22), (37.6, 0.18)):                                        # knuckles on dry fish
        add(fx, t, mixs(ping([(410, 1), (620, 0.5), (980, 0.25)], 0.035, 0.3), burst(200, 2500, 0.05, 0.01, int(t * 10)) * 0.5), g)
    add(fx, 47.4, mixs(burst(60, 2500, 0.3, 0.05, 200), ping([(90, 2)], 0.08, 0.4)), 0.2)  # the blade
    for i in range(22):                                                               # paper
        add(fx, 50.2 + rng.uniform(0, 2.3), burst(2000, 9000, 0.09, 0.03, 300 + i), 0.035)
    pour = band(500, 4500, 80)[: int(1.3 * SR)] * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * np.arange(int(1.3 * SR)) / SR))
    add(fx, 53.1, pour * np.hanning(len(pour)), 0.07)

    def drip(t, g=0.09):
        n = int(0.07 * SR)
        tt = np.arange(n) / SR
        add(fx, t, np.sin(2 * np.pi * (900 * tt + 5000 * tt ** 2)) * np.exp(-tt / 0.02), g)
    for t in (54.9, 56.2, 57.3, 88.5, 89.2, 90.0, 90.5):
        drip(t)
    add(fx, 83.0, mixs(burst(40, 400, 0.6, 0.12, 400), ping([(60, 2)], 0.15, 0.7)), 0.16)  # cold-store door
    for t in (91.3, 91.75, 92.2, 92.65, 93.1):                                        # knife on board
        add(fx, t, mixs(burst(800, 4000, 0.04, 0.008, int(t * 100)), ping([(300, 1)], 0.03, 0.15)), 0.1)
    for i in range(170):                                                              # the simmer
        t = 94.0 + rng.uniform(0, 8.0)
        add(fx, t, ping([(rng.uniform(140, 420), 1)], 0.02, 0.07), 0.03 * (1 - max(0, t - 98) / 5))
    oil = band(300, 2200, 81) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * T) ** 2)
    fx += oil * 0.02 * env(102.5, 106.4, 0.4, 0.5)
    for i in range(16):                                                               # cutlery at the table
        f = rng.uniform(3000, 5200)
        add(fx, 106.8 + rng.uniform(0, 6.5), ping([(f, 1), (f * 1.52, 0.4)], 0.07, 0.4), 0.02)

    # Music: bowed drone and sparse plucked notes, as cued in the script
    dr = drone(73.42) * 0.7 + drone(110.0) * 0.4
    dr_env = (np.clip((T - 12) / 10, 0, 1) * 0.55 + 0.45) * env(12, 50, 0.5, 2.5) \
        + env(62, 88.5, 2.0, 1.5) + 0.6 * env(88, 117, 1.0, 4.0)
    mus += dr * 0.045 * dr_env
    notes = [(22.0, D4, 1), (23.2, A4, .8), (24.6, F4, .8),
             (33.5, D4, .8), (36.2, F4, .7), (38.9, A4, .7), (41.5, G4, .7), (44.2, F4, .7), (46.6, E4, .6), (48.2, D4, .5),
             (62.0, D4, .9), (64.0, A4, .8), (66.0, F4, .8), (68.0, D5, .8), (70.0, A4, .8), (72.0, BB4, .8), (74.0, A4, .8),
             (76.0, F4, .7), (78.0, D4, .6),
             (88.0, D4, 1), (89.5, FS4, .9), (91.0, A4, .9), (92.5, D5, 1), (94.5, B4, .8), (96.5, A4, .8), (98.5, FS4, .8),
             (100.5, G4, .8), (102.5, A4, .8), (104.5, FS4, .8), (106.2, D4, .7), (108.6, A4, .45), (110.6, FS4, .4),
             (114.2, D3, .9), (114.22, D4, .9), (114.3, A4, .7)]
    for i, (t, f, g) in enumerate(notes):
        add(mus, t, pluck(f, 4.5 if t > 114 else 3.2, seed=i), 0.11 * g)

    # Duck music and ambience under the voice
    e = np.abs(vo)
    k = int(0.25 * SR)
    e = np.convolve(e, np.ones(k) / k, "same")
    duck = 1 - 0.5 * np.clip(e / 0.05, 0, 1)
    left = vo + (amb[0] + fx * 0.95 + mus * 1.05) * duck
    right = vo + (amb[1] + fx * 1.05 + mus * 0.95) * duck
    return np.stack([left, right], 1)


def main():
    voice, work, out_wav, out_srt = sys.argv[1:5]
    os.makedirs(work, exist_ok=True)
    vo, placed = narration(voice, work)
    write_srt(placed, out_srt)
    json.dump(placed, open(os.path.join(work, "cues.json"), "w"), indent=1)
    for c in placed:
        print("%6.2f - %6.2f  x%.2f  %s  %s" % (c["start"], c["end"], c["speed"], "ok " if c["fits"] else "LATE", c["text"][:60]))
    mix = soundtrack(vo)
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.95)
    with wave.open(out_wav, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    main()
