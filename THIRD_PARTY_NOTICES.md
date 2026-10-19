# Third-party components, data and media

Bluefin was built by team inki_ponki for FinTechathon 2026. Everything below is used under its own licence or terms;
nothing is copied from another project. Versions are pinned in `backend/requirements.txt` and `mobile/package-lock.json`.

## Code libraries

| Component | Used for | Licence |
|---|---|---|
| FastAPI, Pydantic, PyYAML, pytest | the API, request checks, config, tests | MIT |
| Starlette, Uvicorn, httpx, NumPy, pypdf, qrcode | web server, HTTP client, maths, reading banks' rate sheets, QR codes | BSD |
| cryptography | checking passkey signatures (ECDSA P-256) | Apache-2.0 / BSD |
| Expo SDK and its modules, React, React Native, React Native Web, Expo Router, Reanimated, Gesture Handler, Screens, SVG, Safe Area Context, Worklets | the app (Android and web) | MIT |
| @noble/curves, @noble/hashes | the phone's P-256 key and SHA-256 | MIT |
| @expo/vector-icons (Ionicons) | icons | MIT |
| Inter, Exo 2, Hind Siliguri (via @expo-google-fonts, bundled in the app) | fonts (Latin and Bangla) | SIL Open Font License 1.1 |
| marked (`docs/build/lib/marked.min.js`) | building the PDF documents | MIT |
| Remotion (`video/source/`, not shipped in the app) | rendering the demo video | Remotion License (free for individuals and teams of up to 3) |

## Services and infrastructure

| Service | Used for | Terms |
|---|---|---|
| FISCO BCOS 3.17.1 (official release, unmodified) | the 4-node chain that anchors the evidence log | Apache-2.0 |
| DeepSeek API | the AI's language understanding, only after the user agrees (the key stays on the server) | DeepSeek Open Platform terms |
| Microsoft Azure, Caddy (Apache-2.0), sslip.io | hosting the public demo and its HTTPS address | provider terms |

## Data

| Data | Used for | Terms |
|---|---|---|
| Mid-market exchange rates from `fawazahmed0/currency-api` | the reference rate in quotes | CC0-1.0 (public domain) |
| Eastern Bank PLC's published daily exchange-rate sheets (PDF) | real bank rates and fees in quotes | publicly published by the bank; read, not redistributed |
| Everything else (accounts, balances, payments, the family) | the sandbox | made up for the demo; no real person's financial data |

## Media

- The demo video's music and sound effects are synthesised by `video/source/scripts/gen_audio.py`: no samples or
  stock audio.
- The narration is the team's own voice. The deck and the video also show a real student's interview and photos; they
  are not in this public repository.
