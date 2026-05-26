from typing import Any
import copy
from pathlib import Path
from pydantic import Field
from ten_ai_base import utils
from ten_ai_base.tts2_http import AsyncTTS2HttpConfig


class SpeechmaticsTTSConfig(AsyncTTS2HttpConfig):
    """Speechmatics TTS Config"""

    dump: bool = Field(default=False, description="Speechmatics TTS dump")
    dump_path: str = Field(
        default_factory=lambda: str(
            Path(__file__).parent / "speechmatics_tts_in.pcm"
        ),
        description="Speechmatics TTS dump path",
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Speechmatics TTS params"
    )

    def update_params(self) -> None:
        """Normalize provider params before the client is created."""
        self.params.setdefault("voice", "sarah")
        self.params.setdefault("output_format", "pcm_16000")
        self.params.setdefault(
            "base_url", "https://preview.tts.speechmatics.com"
        )
        self.params.setdefault("sample_rate", 16000)

        self.params["sample_rate"] = int(self.params["sample_rate"])

        # Text is supplied per request by the TEN TTS base extension.
        self.params.pop("text", None)

    def to_str(self, sensitive_handling: bool = True) -> str:
        """Convert config to string with optional sensitive data handling."""
        if not sensitive_handling:
            return f"{self}"

        config = copy.deepcopy(self)

        if config.params and "api_key" in config.params:
            config.params["api_key"] = utils.encrypt(config.params["api_key"])

        return f"{config}"

    def validate(self) -> None:
        """Validate Speechmatics-specific configuration."""
        if "api_key" not in self.params or not self.params["api_key"]:
            raise ValueError("API key is required for Speechmatics TTS")

        if "voice" not in self.params or not self.params["voice"]:
            raise ValueError("Voice is required for Speechmatics TTS")

        if self.params.get("output_format") != "pcm_16000":
            raise ValueError(
                "Speechmatics TTS currently supports only pcm_16000 in this extension"
            )

        if int(self.params.get("sample_rate", 16000)) != 16000:
            raise ValueError(
                "Speechmatics TTS currently supports only 16000 Hz output"
            )
