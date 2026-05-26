from unittest.mock import MagicMock

from speechmatics_tts_python.config import SpeechmaticsTTSConfig
from speechmatics_tts_python.speechmatics_tts import SpeechmaticsTTSClient


def test_client_extra_metadata():
    config = SpeechmaticsTTSConfig.model_validate(
        {
            "params": {
                "api_key": "secret_key",
                "voice": "megan",
                "output_format": "pcm_16000",
                "sample_rate": 16000,
            }
        }
    )
    config.update_params()

    ten_env = MagicMock()
    client = SpeechmaticsTTSClient(config=config, ten_env=ten_env)

    assert client.get_extra_metadata() == {
        "voice": "megan",
        "output_format": "pcm_16000",
    }
