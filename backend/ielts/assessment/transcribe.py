"""Verbatim transcription with faster-whisper; same settings as the YouTube band dataset pipeline."""
import os
import sys
from pathlib import Path

# A prompt full of fillers nudges Whisper to keep um/uh and repetitions instead of cleaning them up.
PROMPT = "Umm, so, uh, I- I mean, well, hmm, you know, like, er, I think... yeah."


class WhisperTranscriber:
    def __init__(self, model: str = "medium.en", device: str | None = None):
        self.model_name = model
        self.device = device or os.environ.get("WHISPER_DEVICE", "cuda")
        self._model = None

    def _load(self):
        if sys.platform == "win32":     # CUDA DLLs come from the nvidia-* pip wheels
            for d in (Path(sys.prefix) / "Lib/site-packages/nvidia").glob("*/bin"):
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        compute = "int8_float16" if self.device == "cuda" else "int8"
        self._model = BatchedInferencePipeline(WhisperModel(self.model_name, device=self.device, compute_type=compute))

    def __call__(self, path: str) -> list[dict]:
        if self._model is None:
            self._load()
        segments, _ = self._model.transcribe(path, language="en", initial_prompt=PROMPT, word_timestamps=True, batch_size=8)
        # plain floats: faster-whisper returns numpy scalars
        return [{"start": float(s.start), "end": float(s.end),
                 "words": [{"w": w.word, "s": float(w.start), "e": float(w.end), "p": round(float(w.probability), 3)} for w in s.words]}
                for s in segments]
