import sys, subprocess, wave, json
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
S = sys.argv[1]; sys.path.insert(0, S + "/pylib")
from faster_whisper import WhisperModel
ff = open(S + "/ffmpeg_path.txt").read().strip()
m = WhisperModel("small", device="cpu", compute_type="int8", download_root=S + "/whisper_models")
res = {}
for name, a, b in [("A", 38.0, 60.0), ("B", 184.0, 206.0)]:
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", sys.argv[2], "-ss", str(a), "-to", str(b), "-vn", "-ac", "1", "-ar", "16000", f"friend_{name}.wav"], check=True)
    with wave.open(f"friend_{name}.wav") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    segs, _ = m.transcribe(x, beam_size=5, word_timestamps=True, language="en")
    ws = [{"w": wd.word.strip(), "s": round(a + wd.start, 2), "e": round(a + wd.end, 2)} for s in segs for wd in s.words]
    res[name] = ws
    print(name, " ".join(f"{w['w']}[{w['s']}-{w['e']}]" for w in ws))
json.dump(res, open("friend_words.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
