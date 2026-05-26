from unittest.mock import AsyncMock, MagicMock

import pytest

from ten_ai_base.struct import TTS2HttpResponseEventType
from speechmatics_tts_python.config import SpeechmaticsTTSConfig
from speechmatics_tts_python.speechmatics_tts import SpeechmaticsTTSClient


class MockResponse:
    def __init__(self, status_code, chunks=None, body=b""):
        self.status_code = status_code
        self.chunks = chunks or []
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def aiter_bytes(self):
        for chunk in self.chunks:
            yield chunk

    async def aread(self):
        return self.body


class CancellingMockResponse(MockResponse):
    def __init__(self, client):
        super().__init__(200)
        self.client = client

    async def aiter_bytes(self):
        self.client._is_cancelled = True
        yield b"\x01\x02"


@pytest.mark.asyncio
async def test_client_streams_sample_aligned_pcm():
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
    ten_env.log_debug = MagicMock()
    ten_env.log_warn = MagicMock()
    ten_env.log_error = MagicMock()

    client = SpeechmaticsTTSClient(config=config, ten_env=ten_env)
    client.client.aclose = AsyncMock()
    client.client.stream = MagicMock(
        return_value=MockResponse(
            200,
            chunks=[b"\x01", b"\x02\x03\x04\x05"],
        )
    )

    events = [event async for event in client.get("hello", "request_1")]
    await client.clean()

    assert events == [
        (b"\x01\x02", TTS2HttpResponseEventType.RESPONSE),
        (b"\x03\x04", TTS2HttpResponseEventType.RESPONSE),
        (None, TTS2HttpResponseEventType.END),
    ]
    client.client.stream.assert_called_once()
    _, kwargs = client.client.stream.call_args
    assert kwargs["json"] == {"text": "hello"}
    assert kwargs["params"] == {"output_format": "pcm_16000"}
    assert kwargs["headers"]["Authorization"] == "Bearer secret_key"


@pytest.mark.asyncio
async def test_client_maps_auth_errors_to_invalid_key():
    config = SpeechmaticsTTSConfig.model_validate(
        {
            "params": {
                "api_key": "bad_key",
                "voice": "sarah",
                "output_format": "pcm_16000",
                "sample_rate": 16000,
            }
        }
    )
    config.update_params()
    ten_env = MagicMock()
    ten_env.log_debug = MagicMock()
    ten_env.log_warn = MagicMock()
    ten_env.log_error = MagicMock()

    client = SpeechmaticsTTSClient(config=config, ten_env=ten_env)
    client.client.aclose = AsyncMock()
    client.client.stream = MagicMock(
        return_value=MockResponse(
            401,
            body=b'{"error": {"message": "invalid token"}}',
        )
    )

    events = [event async for event in client.get("hello", "request_1")]
    await client.clean()

    assert len(events) == 1
    assert events[0][1] == TTS2HttpResponseEventType.INVALID_KEY_ERROR
    assert b"invalid token" in events[0][0]


@pytest.mark.asyncio
async def test_client_emits_flush_on_cancel():
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
    ten_env.log_debug = MagicMock()
    ten_env.log_warn = MagicMock()
    ten_env.log_error = MagicMock()

    client = SpeechmaticsTTSClient(config=config, ten_env=ten_env)
    client.client.aclose = AsyncMock()
    client.client.stream = MagicMock(
        return_value=CancellingMockResponse(client)
    )

    events = [event async for event in client.get("hello", "request_1")]
    await client.clean()

    assert events == [(None, TTS2HttpResponseEventType.FLUSH)]
