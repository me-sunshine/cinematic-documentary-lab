"""Original score for the 50-second pitch film. Every sound is synthesised here, so there is no licence to clear.

The score follows the film:
  0.0 – 7.5   Hook       a held pad; it resolves at 4.1 s when the two worlds connect
  7.5 – 16.5  Business   a quiet plucked pattern enters
  16.5 – 25.5 Execution  a soft pulse joins: structure, then momentum
  25.5 – 37.0 Technology the pulse lifts; a swell leads into the close
  37.0 – 50.0 Close      the pulse drops away, the harmony resolves home and rings out
A soft bell marks each reveal and each evidence figure as it lands.

Usage:  python music.py  ->  out/score.wav (48 kHz stereo). numpy is the only dependency.
"""
import os
import wave

import numpy as np

SR = 48000
LENGTH = 50.0
N = int(SR * LENGTH)
t_all = np.arange(N) / SR
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# Chords in D major: (start, end, bass note, upper voicing), MIDI numbers.
CHORDS = [
    (0.0, 4.0, 47, [59, 62, 66, 69, 73]),     # Bm9: the two worlds, apart
    (4.0, 7.5, 50, [57, 62, 64, 66, 69]),     # Dadd9: connected
    (7.5, 12.0, 43, [55, 59, 62, 66]),        # Gmaj7
    (12.0, 16.5, 50, [57, 62, 64, 66, 69]),   # Dadd9: evidence lands
    (16.5, 21.0, 47, [59, 62, 66, 69]),       # Bm7
    (21.0, 25.5, 45, [57, 61, 64, 69]),       # A
    (25.5, 31.0, 43, [55, 59, 62, 66]),       # Gmaj7
    (31.0, 34.0, 40, [55, 59, 62, 67]),       # Em7
    (34.0, 37.0, 45, [57, 61, 64, 69]),       # A: lift into the close
    (37.0, 43.0, 43, [55, 59, 62, 66, 71]),   # Gmaj9
    (43.0, 50.0, 50, [57, 62, 66, 69, 74]),   # D: home
]
BELLS = [4.1, 7.8, 12.4, 16.8, 21.8, 25.8, 33.0, 39.5, 41.3, 43.0]
BELL_NOTES = [81, 78, 81, 76, 81, 78, 81, 74, 78, 86]
BEAT = 60 / 96


def envelope(start, end, attack, release):
    e = np.zeros(N)
    a, b = int(start * SR), min(N, int(end * SR))
    seg = np.arange(b - a) / SR
    e[a:b] = np.minimum(1, seg / attack) * np.clip((end - start - seg) / release, 0, 1)
    return e


def pad():
    out = np.zeros((N, 2))
    for start, end, bass, notes in CHORDS:
        env = envelope(max(0, start - 0.6), min(LENGTH, end + 0.9), 1.2, 1.5)
        idx = env > 0
        tt = t_all[idx]
        for i, m in enumerate(notes):
            for side, cents in ((0, -4), (1, 4)):
                f = hz(m) * 2 ** (cents / 1200)
                tone = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt + 0.3) + 0.08 * np.sin(6 * np.pi * f * tt)
                shimmer = 0.85 + 0.15 * np.sin(2 * np.pi * (0.13 + 0.05 * i) * tt + i)
                out[idx, side] += 0.045 * tone * shimmer * env[idx]
        b = hz(bass - 12)
        out[idx] += (0.11 * np.sin(2 * np.pi * b * tt) * env[idx])[:, None]
    return out


def pluck(freq, dur=1.6):
    """Karplus-Strong string: a burst of noise filtered round a delay line."""
    p = max(2, int(SR / freq))
    n = int(dur * SR)
    y = np.zeros(n + p)
    y[:p] = rng.uniform(-1, 1, p)
    i = p
    while i < n + p:
        j = min(i + p, n + p)
        prev = y[i - p:j - p]
        prev2 = y[i - p - 1:j - p - 1] if i - p - 1 >= 0 else np.concatenate(([0.0], y[i - p:j - p - 1]))
        y[i:j] = 0.497 * (prev + prev2[:len(prev)])
        i = j
    return y[p:] * np.linspace(1, 0, n) ** 2


def arpeggio():
    out = np.zeros((N, 2))
    step = BEAT / 2
    t, k = 7.5, 0
    while t < 43.0:
        chord = next(c for c in CHORDS if c[0] <= t < c[1])
        tones = sorted(set(chord[3]))
        pattern = [0, 2, 1, 3, 2, 4, 1, 3]
        m = tones[pattern[k % len(pattern)] % len(tones)] + 12
        # quiet when it enters, fuller in the execution and technology scenes, gone for the close
        level = 0.05 if t < 16.5 else 0.075 if t < 37 else 0.05 * max(0, (43 - t) / 6)
        s = pluck(hz(m)) * level
        a = int(t * SR)
        b = min(N, a + len(s))
        pan = 0.5 + 0.3 * np.sin(k * 0.9)
        out[a:b, 0] += s[:b - a] * (1 - pan)
        out[a:b, 1] += s[:b - a] * pan
        t += step
        k += 1
    return out


def pulse():
    out = np.zeros(N)
    kick_t = np.arange(int(0.35 * SR)) / SR
    sweep = 45 + 70 * np.exp(-kick_t * 30)
    kick = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-kick_t * 11)
    hat_t = np.arange(int(0.06 * SR)) / SR
    hat_noise = rng.uniform(-1, 1, len(hat_t))
    hat = np.diff(np.concatenate(([0], hat_noise))) * np.exp(-hat_t * 70)
    t = 16.5
    while t < 43.0:
        level = 0.16 if t < 25.5 else 0.2
        level *= min(1, (t - 16.5) / 2 + 0.3) * (1 if t < 40.5 else max(0, (43 - t) / 2.5))
        a = int(t * SR)
        out[a:a + len(kick)] += kick[:N - a] * level
        if 25.5 <= t < 40.5:
            h = int((t + BEAT / 2) * SR)
            out[h:h + len(hat)] += hat[:max(0, N - h)] * 0.035
        t += BEAT
    return np.stack([out, out], axis=1)


def bells():
    out = np.zeros((N, 2))
    for k, (t, m) in enumerate(zip(BELLS, BELL_NOTES)):
        bt = np.arange(int(3.0 * SR)) / SR
        f = hz(m)
        mod = 2.2 * np.exp(-bt * 4) * np.sin(2 * np.pi * f * 3.5 * bt)
        tone = np.sin(2 * np.pi * f * bt + mod) * np.exp(-bt * 2.2) * 0.07
        a = int(t * SR)
        b = min(N, a + len(tone))
        pan = 0.35 if k % 2 else 0.65
        out[a:b, 0] += tone[:b - a] * (1 - pan)
        out[a:b, 1] += tone[:b - a] * pan
    return out


def swell():
    a, b = int(34.5 * SR), int(37.0 * SR)
    n = b - a
    noise = rng.uniform(-1, 1, n)
    smooth = np.convolve(noise, np.ones(24) / 24, mode="same")
    shape = np.linspace(0, 1, n) ** 2.5
    out = np.zeros((N, 2))
    out[a:b, 0] = smooth * shape * 0.08
    out[a:b, 1] = np.roll(smooth, 300) * shape * 0.08
    return out


def _feedback(x, delay, gain):
    """y[n] = x[n] + gain * y[n - delay], computed a block of `delay` samples at a time."""
    y = x.copy()
    for i in range(delay, len(y), delay):
        j = min(i + delay, len(y))
        y[i:j] += gain * y[i - delay:j - delay]
    return y


def _shift(x, d):
    return np.concatenate((np.zeros(d), x[:-d]))


def reverb(x, wet=0.32):
    """A Freeverb-style room: eight parallel feedback combs, then four allpass filters, per channel."""
    combs = [1215, 1293, 1390, 1476, 1548, 1623, 1695, 1760]     # Freeverb tunings scaled to 48 kHz
    allpasses = [605, 480, 371, 245]
    mono = x.mean(axis=1)
    mono = np.convolve(mono, np.ones(6) / 6, mode="same")         # soften the top end going in
    out = np.zeros_like(x)
    for ch, spread in ((0, 0), (1, 25)):
        acc = np.zeros_like(mono)
        for d in combs:
            acc += _shift(_feedback(mono, d + spread, 0.84), d + spread)
        for d in allpasses:
            b = _feedback(acc, d + spread, 0.5)
            acc = _shift(b, d + spread) - acc
        out[:, ch] = acc
    out *= wet * np.sqrt(np.mean(x ** 2)) / np.sqrt(np.mean(out ** 2))
    return x + out


def main():
    mix = pad() + arpeggio() + pulse() + bells() + swell()
    mix = reverb(mix)
    mix *= np.sqrt(np.mean(mix ** 2)) / np.sqrt(np.mean(mix ** 2, axis=0))   # equal loudness left and right
    mix *= np.minimum(1, t_all / 0.8)[:, None]                          # fade in
    mix *= np.clip((LENGTH - t_all) / 4.0, 0, 1)[:, None] ** 1.5        # ring out over the last 4 s
    mix *= 0.89 / np.max(np.abs(mix))
    os.makedirs("out", exist_ok=True)
    pcm = (mix * 32767).astype("<i2")
    with wave.open("out/score.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("out/score.wav", f"{LENGTH:.1f} s")


if __name__ == "__main__":
    main()
