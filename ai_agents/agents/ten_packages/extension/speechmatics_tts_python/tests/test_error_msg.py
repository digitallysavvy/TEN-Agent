import pytest

from speechmatics_tts_python.config import SpeechmaticsTTSConfig


def test_missing_api_key_error_message():
    config = SpeechmaticsTTSConfig.model_validate({"params": {}})
    config.update_params()

    with pytest.raises(ValueError) as exc_info:
        config.validate()

    assert "API key is required for Speechmatics TTS" in str(exc_info.value)
