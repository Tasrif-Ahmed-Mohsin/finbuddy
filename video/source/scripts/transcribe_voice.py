"""Convert the voice takes to 48 kHz WAV, measure them, and transcribe with word timings (faster-whisper, CPU)."""
import json, subprocess, sys, wave
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
S = Path(sys.argv[1]); src = Path(sys.argv[2]); out = S / "vid" / "voice"
sys.path.insert(0, str(S / "pylib"))
import numpy as np
from faster_whisper import WhisperModel
ff = (S / "ffmpeg_path.txt").read_text().strip()
names = {"Scene 2": "02", "Scene 3": "03", "Scene 4a": "4a", "Scene 4b": "4b", "Scene 4c": "4c", "4d": "4d", "4e": "4e", "4f": "4f",
         "4g": "4g", "4h": "4h", "4i": "4i", "4j": "4j", "Scene 5": "05", "Scene 6": "06", "Scene 8": "08"}
model = WhisperModel("small", device="cpu", compute_type="int8", download_root=str(S / "whisper_models"))
res = {}
for f in sorted(src.glob("*.m4a")):
    key = names[f.stem]
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", "48000", str(out / f"{key}.wav")], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(f), "-ac", "1", "-ar", "16000", str(out / f"{key}_16k.wav")], check=True)
    with wave.open(str(out / f"{key}_16k.wav")) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    segs, info = model.transcribe(x, beam_size=5, word_timestamps=True, language="en")
    words = [{"w": wd.word.strip(), "s": round(wd.start, 2), "e": round(wd.end, 2)} for s in segs for wd in s.words]
    dur = len(x) / 16000
    rms = float(np.sqrt(np.mean(x ** 2))); peak = float(np.max(np.abs(x)))
    res[key] = {"dur": round(dur, 2), "rms_db": round(20 * np.log10(rms + 1e-9), 1), "peak": round(peak, 3), "words": words}
    print(f"{key} {dur:6.2f}s rms {res[key]['rms_db']} dB peak {peak:.2f} | {' '.join(w['w'] for w in words)}", flush=True)
(out / "voice.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("total", round(sum(v["dur"] for v in res.values()), 1))
