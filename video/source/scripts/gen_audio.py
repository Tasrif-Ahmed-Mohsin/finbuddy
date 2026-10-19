"""Synthesize the film's sound: short UI effects and an original ambient music bed that ducks under the voice.
Everything is generated here (no samples, no licences). Writes 48 kHz stereo WAVs into remo/public."""
import json, sys, wave
from pathlib import Path
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 48000
V = Path(sys.argv[1]) / "vid"
PUB = V / "remo" / "public"
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def env_exp(d, tau, attack=0.002):
    t = t_(d)
    a = np.minimum(1, t / attack) if attack > 0 else 1
    return a * np.exp(-t / tau)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def sweep(f0, f1, d, shape="exp"):
    t = t_(d)
    f = f0 * (f1 / f0) ** (t / d) if shape == "exp" else f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def stereo(x, pan=0.0):
    l = x * np.cos((pan + 1) * np.pi / 4)
    r = x * np.sin((pan + 1) * np.pi / 4)
    return np.stack([l, r], 1)


def small_room(x, decay=0.35, mix=0.18):
    ir_t = t_(decay * 2)
    ir = rng.standard_normal((len(ir_t), 2)) * np.exp(-ir_t / decay)[:, None] * 0.03
    if x.ndim == 1:
        x = stereo(x)
    wet = np.stack([fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)
    dry = np.vstack([x, np.zeros((len(wet) - len(x), 2))])
    return dry + mix * wet


def write(name, x, peak=0.8):
    if x.ndim == 1:
        x = stereo(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    fade = min(len(x), int(0.01 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    with wave.open(str(PUB / name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def noise(d):
    return rng.standard_normal(int(d * SR))


# ---------------------------------------------------------------- effects
def sfx():
    out = PUB / "sfx"
    out.mkdir(parents=True, exist_ok=True)
    S = {}
    S["tick"] = np.sin(2 * np.pi * 1900 * t_(0.04)) * env_exp(0.04, 0.008) + 0.2 * hp(noise(0.04), 4000) * env_exp(0.04, 0.003)
    S["pop"] = sweep(480, 1150, 0.16) * env_exp(0.16, 0.05, 0.003) + 0.3 * np.sin(2 * np.pi * 240 * t_(0.16)) * env_exp(0.16, 0.03)
    S["tap"] = 0.6 * hp(noise(0.05), 2500) * env_exp(0.05, 0.004) + np.sin(2 * np.pi * 170 * t_(0.05)) * env_exp(0.05, 0.015)
    d = 0.6
    t = t_(d)
    wn = noise(d)
    lo = bp(wn, 250, 900, 2) * np.sin(np.pi * t / d) ** 2
    hi = bp(wn, 1500, 5000, 2) * np.sin(np.pi * np.clip(t / d * 1.2, 0, 1)) ** 3
    w = np.stack([(0.7 * lo + 0.5 * hi) * np.linspace(1, 0.4, len(t)), (0.7 * lo + 0.5 * hi) * np.linspace(0.4, 1, len(t))], 1)
    S["whoosh"] = w
    d = 0.3
    S["swipe"] = stereo(bp(noise(d), 1200, 6000) * np.sin(np.pi * t_(d) / d) ** 2, 0.3)
    d = 0.8
    t = t_(d)
    r = (bp(noise(d), 800, 6000) * 0.4 + 0.5 * sweep(180, 1300, d)) * (t / d) ** 2
    r[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    S["rise"] = r
    d = 1.8
    t = t_(d)
    shimmer = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9) * a for f, a in [(1046.5, 0.5), (1318.5, 0.4), (1568, 0.35), (1975.5, 0.25), (2093, 0.2)])
    boom = np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.35)
    S["reveal"] = small_room(0.6 * shimmer * np.minimum(1, t / 0.02) + 0.9 * boom, 0.6, 0.35)
    d = 0.45
    t = t_(d)
    S["crack"] = 0.9 * hp(noise(d), 1500) * env_exp(d, 0.02) + 0.4 * bp(noise(d), 300, 2000) * env_exp(d, 0.09) * (rng.random(len(t)) > 0.7) + 0.8 * np.sin(2 * np.pi * 80 * t) * env_exp(d, 0.06)
    d = 0.6
    t = t_(d)
    S["stamp"] = small_room(1.0 * np.sin(2 * np.pi * 62 * t) * env_exp(d, 0.11, 0.001) + 0.5 * lp(noise(d), 2500) * env_exp(d, 0.025), 0.25, 0.25)
    d = 0.9
    t = t_(d)
    S["hit"] = small_room(np.sin(2 * np.pi * np.cumsum(np.linspace(90, 42, len(t))) / SR) * env_exp(d, 0.22, 0.001) + 0.35 * lp(noise(d), 1800) * env_exp(d, 0.04), 0.5, 0.3)
    beep = lambda f, d: np.sin(2 * np.pi * f * t_(d)) * np.minimum(1, t_(d) / 0.01) * np.exp(-t_(d) / 0.12)
    S["alert"] = np.concatenate([beep(880, 0.14), beep(660, 0.22)])
    mar = lambda f, d: (np.sin(2 * np.pi * f * t_(d)) + 0.3 * np.sin(2 * np.pi * 4 * f * t_(d)) * np.exp(-t_(d) / 0.03)) * env_exp(d, 0.15)
    S["notify"] = small_room(np.concatenate([mar(659.3, 0.11), mar(987.8, 0.45)]), 0.3, 0.2)
    notes = [523.3, 659.3, 784.0, 1046.5]
    d = 1.2
    t = t_(d)
    succ = np.zeros(len(t))
    for i, f in enumerate(notes):
        k = int(i * 0.07 * SR)
        n = len(t) - k
        succ[k:] += (np.sin(2 * np.pi * f * t[:n]) + 0.25 * np.sin(2 * np.pi * 2 * f * t[:n])) * np.exp(-t[:n] / 0.35) * 0.6
    S["success"] = small_room(succ, 0.4, 0.25)
    d = 1.6
    t = t_(d)
    S["chime"] = small_room(sum(np.sin(2 * np.pi * 1046.5 * r * t) * a * np.exp(-t / (0.9 / r)) for r, a in [(1, 1), (2.76, 0.45), (5.4, 0.25), (8.93, 0.12)]), 0.5, 0.3)
    click = lambda: hp(noise(0.03), 2000) * env_exp(0.03, 0.003)
    lk = np.zeros(int(0.35 * SR))
    lk[: len(click())] += click()
    k = int(0.05 * SR)
    lk[k:k + int(0.03 * SR)] += click() * 1.2
    lk[k:] += 0.25 * np.sin(2 * np.pi * 2600 * t_(0.35)[: len(lk) - k]) * np.exp(-t_(0.35)[: len(lk) - k] / 0.05)
    S["lock"] = lk
    d = 1.7
    ty = np.zeros(int(d * SR))
    pos = 0.0
    while pos < d - 0.06:
        k = int(pos * SR)
        c = bp(noise(0.04), 1500, 6000) * env_exp(0.04, 0.006) * (0.6 + 0.4 * rng.random())
        ty[k:k + len(c)] += c
        pos += 0.07 + 0.08 * rng.random()
    S["type"] = ty
    d = 0.5
    t = t_(d)
    coin = np.concatenate([np.sin(2 * np.pi * 1975.5 * t_(0.08)) * env_exp(0.08, 0.05), np.sin(2 * np.pi * 2637 * t) * env_exp(d, 0.18)])
    S["coin"] = small_room(coin, 0.3, 0.2)
    d = 0.9
    t = t_(d)
    S["rewind"] = bp(noise(d), 600, 5000) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(np.linspace(30, 8, len(t))) / SR)) * np.sin(np.pi * t / d) + 0.3 * sweep(900, 300, d) * np.sin(np.pi * t / d)
    d = 1.0
    t = t_(d)
    S["print"] = bp(noise(d), 300, 3000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 28 * t))) * np.sin(np.pi * t / d) ** 0.5 * 0.6
    d = 0.7
    t = t_(d)
    S["scan"] = (0.5 * sweep(400, 1600, d) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t)) + 0.3 * bp(noise(d), 2000, 7000)) * np.sin(np.pi * t / d)
    for k, x in S.items():
        write(f"sfx/{k}.wav", x, 0.85)
    print("sfx", len(S))


# ---------------------------------------------------------------- music
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


CH = {  # chord tones (MIDI), voiced in the middle register
    "Bm7": [47, 54, 57, 62, 66], "Gmaj7": [43, 55, 59, 62, 66], "Dmaj7": [50, 54, 57, 61, 64], "Asus": [45, 52, 57, 59, 64],
    "D": [50, 54, 57, 62, 66], "A": [45, 52, 57, 61, 64], "Bm": [47, 54, 59, 62, 66], "G": [43, 50, 59, 62, 67], "Dadd9": [50, 57, 62, 64, 66],
}


def pad_chord(name, d):
    t = t_(d)
    x = np.zeros(len(t))
    for n in CH[name]:
        f = midi(n)
        for det in (-0.006, 0.0, 0.0065):
            ff = f * (1 + det)
            for h in range(1, 9):
                if ff * h > 6000:
                    break
                x += np.sin(2 * np.pi * ff * h * t + rng.random() * 6.28) * (1 / h) * np.exp(-h / 2.6)
    return x / len(CH[name])


def music(total, scenes):
    n = int(total * SR)
    mix = np.zeros((n, 2))
    sections = [(0.0, 45.2, ["Bm7", "Gmaj7", "Dmaj7", "Asus"], False), (45.2, 269.5, ["D", "A", "Bm", "G"], True), (269.5, total, ["Gmaj7", "Dadd9"], False)]
    CHORD = 5.0
    cache = {}
    for (a, b, prog, arp) in sections:
        k = 0
        s = a
        while s < b - 0.5:
            name = prog[k % len(prog)]
            d = min(CHORD, b - s) + 1.6
            if (name, round(d, 2)) not in cache:
                cache[(name, round(d, 2))] = pad_chord(name, d)
            x = cache[(name, round(d, 2))].copy()
            tt = t_(d)
            e = np.minimum(1, tt / 1.2) * np.minimum(1, (d - tt) / 1.6)
            i0 = int(s * SR)
            i1 = min(n, i0 + len(x))
            seg = (x * e)[: i1 - i0]
            mix[i0:i1, 0] += seg * 0.9
            mix[i0:i1, 1] += np.roll(seg, 240) * 0.9
            # sub bass on the root
            root = midi(CH[name][0] - 12)
            for beat in range(int(min(CHORD, b - s) / 1.25)):
                j0 = i0 + int(beat * 1.25 * SR)
                bd = t_(1.1)
                sb = np.sin(2 * np.pi * root * bd) * np.exp(-bd / 0.45) * np.minimum(1, bd / 0.01) * (0.55 if arp else 0.35)
                j1 = min(n, j0 + len(sb))
                mix[j0:j1] += stereo(sb[: j1 - j0])
            if arp:
                tones = sorted(CH[name][1:]) + [CH[name][1] + 12]
                pattern = [0, 2, 4, 5, 3, 1, 2, 4]
                step = 60 / 96 / 2
                for st in range(int(min(CHORD, b - s) / step)):
                    nn = tones[pattern[st % len(pattern)] % len(tones)] + 12
                    f = midi(nn)
                    pd = t_(0.5)
                    pl = (np.sin(2 * np.pi * f * pd) + 0.25 * np.sin(2 * np.pi * 2 * f * pd) * np.exp(-pd / 0.05)) * np.exp(-pd / 0.22) * np.minimum(1, pd / 0.004)
                    j0 = i0 + int(st * step * SR)
                    j1 = min(n, j0 + len(pl))
                    mix[j0:j1] += stereo(pl[: j1 - j0] * 0.16, 0.45 if st % 2 else -0.45)
                    if st % 2 == 1:  # soft shaker on the off-beat
                        sh = hp(noise(0.06), 6000) * env_exp(0.06, 0.012) * 0.05
                        j1 = min(n, j0 + len(sh))
                        mix[j0:j1] += stereo(sh[: j1 - j0], 0.2)
            s += CHORD
            k += 1
    # reverb
    ir_t = t_(3.0)
    ir = rng.standard_normal((len(ir_t), 2)) * np.exp(-ir_t / 0.9)[:, None]
    ir[:, 0] = lp(ir[:, 0], 5000)
    ir[:, 1] = lp(ir[:, 1], 5000)
    ir /= np.sqrt((ir ** 2).sum(0))
    wet = np.stack([fftconvolve(mix[:, c], ir[:, c])[:n] for c in range(2)], 1)
    out = 0.7 * mix + 0.6 * wet
    out = lp(out.T, 7000).T
    # duck under speech: voice loudness per frame from the timeline
    fr = np.zeros(int(total * 30) + 2)
    for s in scenes:
        st = s["from"] + round(s["lead"] * 30)
        env = np.array(s["env"])
        fr[st:st + len(env)] = np.maximum(fr[st:st + len(env)], env)
    act = np.convolve((fr > 0.08).astype(float), np.ones(24) / 24, mode="same")  # smoothed speech activity
    g = 1.0 - 0.6 * np.clip(act * 1.6, 0, 1)
    gs = np.interp(np.arange(n) / SR * 30, np.arange(len(g)), g)
    out *= gs[:, None]
    # intro and outro
    fade_in = np.minimum(1, np.arange(n) / (2.0 * SR))
    fade_out = np.clip((total - np.arange(n) / SR) / 3.0, 0, 1)
    out *= (fade_in * fade_out)[:, None]
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.5
    rms = np.sqrt(np.mean(out ** 2))
    print("music rms dBFS", round(20 * np.log10(rms), 1))
    with wave.open(str(PUB / "music.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    sfx()
    tl = json.load(open(V / "remo" / "src" / "timeline.json", encoding="utf-8"))
    music(tl["frames"] / 30, tl["scenes"])
