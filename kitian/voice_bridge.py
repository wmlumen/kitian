"""Bridge mínimo para exponer voice_gateway desde rutas legacy/backward-compat."""
from __future__ import annotations

from kitian.voice_gateway import (  # noqa: F401
    _ensure_wakeword,
    _get_voice_state,
    _handle_speak,
    _handle_wakeword_toggle,
    _handle_ptt,
    _set_voice_state,
    _do_audio_pipeline,
    _handle_transcription,
    _wakeword_loop,
    _wakeword_stop,
    _wakeword_lock,
    start_background,
)
