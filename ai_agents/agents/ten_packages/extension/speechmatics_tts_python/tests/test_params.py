import pytest

from speechmatics_tts_python.config import SpeechmaticsTTSConfig


def test_config_defaults_and_redaction():
    config = SpeechmaticsTTSConfig.model_validate(
        {"params": {"api_key": "secret_key"}}
    )
    config.update_params()
    config.validate()

    assert config.params["voice"] == "sarah"
    assert config.params["output_format"] == "pcm_16000"
    assert config.params["sample_rate"] == 16000
    assert config.params["base_url"] == "https://preview.tts.speechmatics.com"
    assert "secret_key" not in config.to_str()


def test_config_rejects_missing_api_key():
    config = SpeechmaticsTTSConfig.model_validate({"params": {"api_key": ""}})
    config.update_params()

    with pytest.raises(ValueError, match="API key"):
        config.validate()


def test_config_rejects_non_16000_sample_rate():
    config = SpeechmaticsTTSConfig.model_validate(
        {
            "params": {
                "api_key": "secret_key",
                "sample_rate": 24000,
            }
        }
    )
    config.update_params()

    with pytest.raises(ValueError, match="16000"):
        config.validate()


def test_config_rejects_non_pcm_16000_output_format():
    config = SpeechmaticsTTSConfig.model_validate(
        {
            "params": {
                "api_key": "secret_key",
                "output_format": "wav_16000",
            }
        }
    )
    config.update_params()

    with pytest.raises(ValueError, match="pcm_16000"):
        config.validate()
