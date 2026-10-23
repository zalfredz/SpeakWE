"""Browser recordings (webm/opus or mp4/aac) → mono 16 kHz MP3, a format Gemini accepts inline."""
import subprocess

import imageio_ffmpeg


def to_mp3(path: str) -> bytes:
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-b:a", "32k", "-f", "mp3", "pipe:1"]
    out = subprocess.run(cmd, capture_output=True, timeout=120)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(out.stderr.decode(errors="replace")[:300] or "ffmpeg produced no audio")
    return out.stdout
