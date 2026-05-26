from unittest.mock import AsyncMock, MagicMock

import pytest

from ten_ai_base.struct import TTS2HttpResponseEventType
from speechmatics_tts_python.config import SpeechmaticsTTSConfig
from speechmatics_tts_python.speechmatics_tts import SpeechmaticsTTSClient


@pytest.mark.asyncio
async def test_client_maps_connection_errors_to_error_event():
    config = SpeechmaticsTTSConfig.model_validate(
        {
            "params": {
                "api_key": "secret_key",
                "voice": "sarah",
                "output_format": "pcm_16000",
                "sample_rate": 16000,
            }
        }
    )
    config.update_params()
    ten_env = MagicMock()
    ten_env.log_error = MagicMock()
    ten_env.log_warn = MagicMock()
    ten_env.log_debug = MagicMock()

    client = SpeechmaticsTTSClient(config=config, ten_env=ten_env)
    client.client.aclose = AsyncMock()
    client.client.stream = MagicMock(side_effect=ConnectionError("drop"))

    events = [event async for event in client.get("hello", "request_1")]
    await client.clean()

    assert len(events) == 1
    assert events[0][1] == TTS2HttpResponseEventType.ERROR
    assert b"drop" in events[0][0]
