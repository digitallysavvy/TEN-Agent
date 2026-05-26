from typing import Any, AsyncIterator, Tuple
import json
from urllib.parse import quote

from httpx import AsyncClient, Timeout, Limits
from ten_runtime import AsyncTenEnv
from ten_ai_base.const import LOG_CATEGORY_VENDOR
from ten_ai_base.struct import TTS2HttpResponseEventType
from ten_ai_base.tts2_http import AsyncTTS2HttpClient

from .config import SpeechmaticsTTSConfig


BYTES_PER_SAMPLE = 2
NUMBER_OF_CHANNELS = 1


class SpeechmaticsTTSClient(AsyncTTS2HttpClient):
    """Speechmatics TTS HTTP streaming client."""

    def __init__(
        self,
        config: SpeechmaticsTTSConfig,
        ten_env: AsyncTenEnv,
    ):
        super().__init__()
        self.config = config
        self.ten_env: AsyncTenEnv = ten_env
        self._is_cancelled = False

        api_key = self.config.params.get("api_key", "")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        self.client = AsyncClient(
            timeout=Timeout(timeout=60.0),
            limits=Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=600.0,
            ),
            http2=True,
        )

    async def cancel(self):
        """Cancel the current TTS request."""
        self.ten_env.log_debug("SpeechmaticsTTS: cancel() called.")
        self._is_cancelled = True

    def _url(self) -> str:
        base_url = self.config.params.get(
            "base_url", "https://preview.tts.speechmatics.com"
        ).rstrip("/")
        voice = quote(str(self.config.params.get("voice", "sarah")), safe="")
        return f"{base_url}/generate/{voice}"

    async def get(
        self, text: str, request_id: str
    ) -> AsyncIterator[Tuple[bytes | None, TTS2HttpResponseEventType]]:
        """Process a single TTS request."""
        self._is_cancelled = False

        if len(text.strip()) == 0:
            self.ten_env.log_warn(
                f"SpeechmaticsTTS: empty text for request_id: {request_id}.",
                category=LOG_CATEGORY_VENDOR,
            )
            yield None, TTS2HttpResponseEventType.END
            return

        try:
            params = {
                "output_format": self.config.params.get(
                    "output_format", "pcm_16000"
                )
            }

            async with self.client.stream(
                "POST",
                self._url(),
                headers=self.headers,
                params=params,
                json={"text": text},
            ) as response:
                if self._is_cancelled:
                    self.ten_env.log_debug(
                        f"Cancellation detected before processing response for request_id: {request_id}"
                    )
                    yield None, TTS2HttpResponseEventType.FLUSH
                    return

                if response.status_code < 200 or response.status_code >= 300:
                    error_body = await response.aread()
                    error_msg = self._parse_error_body(error_body)

                    self.ten_env.log_error(
                        f"vendor_error: HTTP {response.status_code}: {error_msg} for request_id: {request_id}",
                        category=LOG_CATEGORY_VENDOR,
                    )

                    if response.status_code in (401, 403):
                        yield error_msg.encode(
                            "utf-8"
                        ), TTS2HttpResponseEventType.INVALID_KEY_ERROR
                    else:
                        yield error_msg.encode(
                            "utf-8"
                        ), TTS2HttpResponseEventType.ERROR
                    return

                cache_audio_bytes = bytearray()
                async for chunk in response.aiter_bytes():
                    if self._is_cancelled:
                        self.ten_env.log_debug(
                            f"Cancellation detected, flushing TTS stream for request_id: {request_id}"
                        )
                        yield None, TTS2HttpResponseEventType.FLUSH
                        break

                    if len(cache_audio_bytes) > 0:
                        chunk = bytes(cache_audio_bytes) + chunk
                        cache_audio_bytes = bytearray()

                    left_size = len(chunk) % (
                        BYTES_PER_SAMPLE * NUMBER_OF_CHANNELS
                    )
                    if left_size > 0:
                        cache_audio_bytes = bytearray(chunk[-left_size:])
                        chunk = chunk[:-left_size]

                    if len(chunk) > 0:
                        self.ten_env.log_debug(
                            f"SpeechmaticsTTS: received audio chunk, length: {len(chunk)} for request_id: {request_id}"
                        )
                        yield bytes(chunk), TTS2HttpResponseEventType.RESPONSE

                if len(cache_audio_bytes) > 0 and not self._is_cancelled:
                    self.ten_env.log_warn(
                        f"SpeechmaticsTTS: dropped incomplete PCM sample, length: {len(cache_audio_bytes)} for request_id: {request_id}",
                        category=LOG_CATEGORY_VENDOR,
                    )

                if not self._is_cancelled:
                    self.ten_env.log_debug(
                        f"SpeechmaticsTTS: sending END event for request_id: {request_id}"
                    )
                    yield None, TTS2HttpResponseEventType.END

        except Exception as e:
            error_message = str(e)
            self.ten_env.log_error(
                f"vendor_error: {error_message} for request_id: {request_id}",
                category=LOG_CATEGORY_VENDOR,
            )
            if "401" in error_message or "403" in error_message:
                yield error_message.encode(
                    "utf-8"
                ), TTS2HttpResponseEventType.INVALID_KEY_ERROR
            else:
                yield error_message.encode(
                    "utf-8"
                ), TTS2HttpResponseEventType.ERROR

    def _parse_error_body(self, error_body: bytes) -> str:
        try:
            error_data = json.loads(error_body)
            if isinstance(error_data, dict):
                error = error_data.get("error")
                if isinstance(error, dict):
                    return str(error.get("message", error))
                if error:
                    return str(error)
                message = error_data.get("message")
                if message:
                    return str(message)
            return str(error_data)
        except Exception:
            return error_body.decode("utf-8", errors="replace")

    async def clean(self):
        """Clean up HTTP client resources."""
        self.ten_env.log_debug("SpeechmaticsTTS: clean() called.")
        try:
            await self.client.aclose()
        finally:
            pass

    def get_extra_metadata(self) -> dict[str, Any]:
        """Return extra metadata for TTFB metrics."""
        return {
            "voice": self.config.params.get("voice", ""),
            "output_format": self.config.params.get("output_format", ""),
        }
