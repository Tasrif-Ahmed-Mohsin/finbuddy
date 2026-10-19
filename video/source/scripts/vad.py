import json, wave, sys
import numpy as np
d = json.load(open('voice/voice.json', encoding='utf-8'))
out = {}
for k in d:
    with wave.open(f'voice/{k}.wav') as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    win = int(sr * 0.02); n = len(x) // win
    r = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1)) + 1e-9
    db = 20 * np.log10(r)
    floor = np.percentile(db, 10); peak = np.percentile(db, 98)
    thr = floor + 0.25 * (peak - floor)
    voiced = np.where(db > thr)[0]
    a, b = voiced[0] * 0.02, (voiced[-1] + 1) * 0.02
    out[k] = {'start': round(max(0, a - 0.15), 2), 'end': round(min(n * 0.02, b + 0.3), 2)}
    print(k, f'floor {floor:.1f} dB, speech {peak:.1f} dB, thr {thr:.1f}', 'voiced', round(a, 2), round(b, 2), 'of', round(n * 0.02, 2))
json.dump(out, open('voice/trim.json', 'w'), indent=1)
