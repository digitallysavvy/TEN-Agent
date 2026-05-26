import pytest

from speechmatics_tts_python.config import SpeechmaticsTTSConfig
from speechmatics_tts_python.extension import SpeechmaticsTTSExtension


@pytest.mark.asyncio
async def test_extension_creates_config_and_reports_fixed_sample_rate():
    extension = SpeechmaticsTTSExtension("speechmatics_tts_python")
    config = await extension.create_config(
        '{"params": {"api_key": "secret_key", "voice": "sarah"}}'
    )

    assert isinstance(config, SpeechmaticsTTSConfig)
    config.update_params()
    config.validate()
    assert extension.synthesize_audio_sample_rate() == 16000
