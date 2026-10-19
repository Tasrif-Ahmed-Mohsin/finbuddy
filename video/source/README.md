# Bluefin demo video: source

The finished film is `video/Bluefin_Demo.mp4` (4:52, 1080p30, −14 LUFS). It is git-ignored, like every recording.

The film is code: a [Remotion](https://www.remotion.dev) 4.0.531 project. Every animation is keyed to the word being spoken, through the word timings of the voice takes.

## Pipeline

1. **Voice and word timings:** `scripts/transcribe_voice.py`, then `scripts/vad.py`.
   - These read the takes in `video/Audio of speech/Audio tasrif/`.
   - faster-whisper gives the word timings; the energy check finds where speech starts and ends.
2. **Friend clips:** `scripts/friend_words.py`.
   - These come from `video/WIN_20261018_20_33_27_Pro.mp4`.
   - Its audio track has timestamp gaps, so the clips are cut from one full extraction, never with `-ss` on the input.
3. **Timeline:** `scripts/make_timeline.py`.
   - Trims and levels each take.
   - Aligns the clean captions to the spoken words.
   - Writes `remotion/src/timeline.json`.
4. **App screens:** `scripts/capture_hi.js` (with `run_local.js`).
   - Takes 3× stills of the real app.
   - The story is captured on a local server; the FISCO BCOS proof screen comes from the live server.
5. **Sound:** `scripts/gen_audio.py` synthesises the 20 effects and the music bed. There are no samples and no licences.
6. **Render:**
   - In `remotion/`, run `render_video.mjs` (muted) and `render_audio.mjs`.
   - Join the two with ffmpeg.
   - Run `scripts/post.py` to level to −14 LUFS.
   - Convert to BT.709 / yuv420p.

Scenes are `remotion/src/scenesA.tsx` to `scenesE.tsx`. Shared motion pieces live in `lib.tsx`: kinetic text, counters, the phone, stamps and tap ripples. The app's robot, redrawn, is `Mascot.tsx`.

Media is not kept here (voice, friend clips, screenshots, music). Re-create it with the scripts above.

**Windows note:** something on this PC deletes empty folders in `%TEMP%` during long jobs. Remotion's audio mixer then fails at the end. The local `@remotion/renderer` was patched to recreate its temp folders right before use.
