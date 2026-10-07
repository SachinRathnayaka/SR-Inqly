## SR Inqly 2.1.2

Draw, highlight, write and capture directly over your Windows desktop.

### Improvements

- Select and erase neon strokes using the same smooth curve shown on screen.
- Reuse cached fade geometry instead of rebuilding every curve each frame.
- Encode screenshot PNGs in a background worker with bounded memory and queue size.
- Limit full-screen captures to 32 million pixels and restore the toolbar after capture errors.
- Package tracked source files only, reject private material patterns and include a source manifest.
- Verify executable/installer versions, ZIP integrity and SHA-256 checksums during packaging.
- Clarify the license: free personal/non-commercial app use; commercial use requires the developer's written permission.

### Downloads

| File | Purpose |
| --- | --- |
| `SR.Inqly.Setup.2.1.2.exe` | Windows installer |
| `SR-Inqly-2.1.2-Windows-Portable.zip` | Extract fully and launch `SR Inqly.exe` |
| `SR-Inqly-2.1.2-Source.zip` | Source, documentation, tests and build definitions |
| `SHA256SUMS-2.1.2.txt` | Verify the three download files without recompressing them |

### Requirements and notes

- Windows 10/11, 64-bit. Python is not required for the binary downloads.
- These Windows binaries are unsigned. A trusted signing certificate is required for publisher signing.
- Original source is under `LICENSE`; third-party components retain their own licenses. See `THIRD_PARTY_NOTICES.md`.
- Mixed-DPI dual 4K, 120/144 Hz, sleep/wake and a 30–60 minute hardware soak remain unverified.

**Developed by Sachin Rathnayaka**

[Documentation and screenshots](https://github.com/SachinRathnayaka/SR-Inqly#readme)
