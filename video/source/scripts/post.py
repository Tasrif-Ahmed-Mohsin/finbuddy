"""Level the finished film's audio to -14 LUFS (true peak -1.5 dB) and copy the video stream untouched."""
import json, subprocess, sys
from pathlib import Path
S = Path(sys.argv[1]); src, dst = sys.argv[2], sys.argv[3]
FF = (S / "ffmpeg_path.txt").read_text().strip()
p = subprocess.run([FF, "-hide_banner", "-i", src, "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
print("measured", {k: m[k] for k in ("input_i", "input_tp", "input_lra")})
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-c:v", "copy", "-af", f"{ln},alimiter=limit=0.84:level=false",
                "-ar", "48000", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", dst], check=True)
p = subprocess.run([FF, "-hide_banner", "-i", dst, "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
print("final", {k: m[k] for k in ("input_i", "input_tp", "input_lra")})
