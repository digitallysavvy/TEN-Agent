# Plan: Add Speechmatics TTS Extension to TEN Framework

## 1) Current context and goal
- Goal: Add a new `speechmatics_tts` extension in the same `agents/ten_packages/extension/` model as existing providers.
- Existing foundation: `speechmatics_asr_python` is already present and already uses the Speechmatics SDK, so we can reuse naming, packaging, and security patterns.
- Baseline for implementation style: `openai_tts2_python` (simple init/config/tests layout) and `deepgram_tts` / `stepfun_tts_python` (state machine/event handling style for streaming/cancel/flush).
- No runtime changes yet; this is a pre-implementation plan only.

## 2) Minimal implementation strategy
- Create `speechmatics_tts_python` as a new extension package (new extension, not in-place mutation of ASR).
- Keep architecture small:
  - Config + client isolated in dedicated files.
  - Use `AsyncTTS2HttpExtension`, because Speechmatics TTS is HTTP streaming output, not a bidirectional WebSocket API.
  - Model the implementation after recent HTTP TTS providers such as `openai_tts2_python`, `groq_tts_python`, and `rime_http_tts`.
  - Request `pcm_16000` directly from Speechmatics so TEN receives raw PCM instead of WAV data that needs header stripping.
  - Emit 16 kHz, 16-bit signed integer, mono, little-endian PCM.
  - Use `httpx.AsyncClient` for async streaming response consumption unless a repo-approved reason appears to use `speechmatics-tts`.

## 2a) Speechmatics API contract to implement
- Endpoint:
  - Default base URL: `https://preview.tts.speechmatics.com`
  - Request path: `/generate/<voice_id>`
  - Query: `output_format=pcm_16000`
- Method: `POST`
- Headers:
  - `Authorization: Bearer <api_key>`
  - `Content-Type: application/json`
- Body:
  - `{"text": "<tts text>"}`
- Supported voices in the current quickstart:
  - `sarah` - English Female (UK)
  - `theo` - English Male (UK)
  - `megan` - English Female (US)
  - `jack` - English Male (US)
- Output:
  - raw PCM, 16 kHz, 16-bit signed integer, mono, little-endian
  - chunks should be sample-aligned before being yielded to the TEN HTTP TTS base.

## 3) Files to add
(under `ai_agents/agents/ten_packages/extension/speechmatics_tts_python/`)

### Required package files
- `addon.py`
  - Register addon `speechmatics_tts_python` and construct extension class.
- `extension.py`
  - Core implementation:
    - `vendor()` returns `"speechmatics"`.
    - Inherit from `AsyncTTS2HttpExtension`.
    - Implement `create_config()`, `create_client()`, and `synthesize_audio_sample_rate()`.
    - Return `16000` from `synthesize_audio_sample_rate()`.
- `config.py`
  - Pydantic model with:
    - `params.api_key`: required for bearer auth
    - `params.voice`: default `sarah`
    - `params.output_format`: default `pcm_16000`
    - `params.base_url`: default `https://preview.tts.speechmatics.com`
    - `params.sample_rate`: default `16000`; reject non-16000 values unless Speechmatics expands supported output formats
    - flags: `dump`, `dump_path`
    - `params` dict passthrough.
  - Implement `to_str(sensitive_handling=True)` to redact credentials.
  - Implement `validate()` + `update_params()` with provider key extraction semantics.
- `speechmatics_tts.py` (or equivalent client module)
  - Implement an `AsyncTTS2HttpClient` subclass.
  - Build the URL as `<base_url>/generate/<voice>?output_format=pcm_16000`.
  - Stream response bytes using `httpx`.
  - Align chunks to 2-byte samples before yielding `TTS2HttpResponseEventType.RESPONSE`.
  - On cancel, stop streaming and yield `TTS2HttpResponseEventType.FLUSH`.
  - Map `401`/`403` to `INVALID_KEY_ERROR`; map other non-2xx responses to `ERROR`.
  - Include `get_extra_metadata()` with `voice` and `output_format` for metrics.
- `manifest.json`
  - `type/name/version/dependencies` aligned with others
  - `api-interface`: `../../system/ten_ai_base/api/tts-interface.json`
  - property schema for `api_key`, `voice`, `output_format`, `base_url`, and `sample_rate`
- `property.json`
  - default sane params with env substitution:
    - `api_key`: `${env:SPEECHMATICS_API_KEY|}`
    - `voice`: `sarah`
    - `output_format`: `pcm_16000`
    - `sample_rate`: `16000`
- `requirements.txt`
  - include `httpx`
  - do not add `speechmatics-python` unless the implementation intentionally uses the ASR SDK
  - do not add `speechmatics-tts` unless it proves materially simpler than the existing HTTP TTS client pattern
- `README.md`
  - provider config matrix, env var, sample graph fragment, supported params.
- `__init__.py`
  - package marker

### Tests
- `tests/bin/start`
- `tests/conftest.py` (copy from extension test fixtures style)
- `tests/configs/`
  - `property_basic_audio_setting1.json`
  - `property_basic_audio_setting2.json`
  - `property_dump.json`
  - `property_miss_required.json`
  - `property_invalid.json`
- `tests/test_basic.py`
- `tests/test_error_msg.py`
- `tests/test_metrics.py`
- `tests/test_state_machine.py`
- `tests/test_robustness.py`
- Optional: `tests/test_params.py` if params redaction/normalization needs dedicated coverage
- Because Speechmatics currently documents only 16 kHz TTS output, both basic audio setting configs should use `sample_rate: 16000`. If the TTS guarder requires sample-rate variation, run it with sample-rate comparison disabled and document that reason.

## 4) Files to edit (integration points)
- `ai_agents/agents/examples/voice-assistant/tenapp/manifest.json`
  - Add package path for `../../../ten_packages/extension/speechmatics_tts_python`.
- `ai_agents/agents/examples/voice-assistant/tenapp/property.json`
  - Add a new graph variant (recommended: `voice_assistant_speechmatics_tts`) or add a graph option beside existing `voice_assistant`.
  - Keep graph wiring unchanged except:
    - swap/add TTS node `addon: speechmatics_tts_python`
    - ensure `tts` node data flow remains `main_control -> tts -> agora_rtc` and flush/stop wiring stays intact.
- `ai_agents/agents/examples/voice-assistant/README.md`
  - Add env var entry (`SPEECHMATICS_TTS_KEY` if using that var name)
  - Add graph name description so consumers can pick it in docs.
- If docs/reference lists supported TTS providers elsewhere, add speechmatics row there as second pass.
- No frontend `moduleConfig.ts` update is expected for the `voice-assistant` graph picker path unless implementation shows the selected example uses a provider config UI that hardcodes TTS providers. Existing Speechmatics frontend entries found locally are ASR-only in other examples.

## 5) Config/API research checkpoints before implementation (required)
- Already confirmed from the current Speechmatics TTS quickstart:
  - bearer auth
  - HTTP `POST`
  - voice-specific `/generate/<voice_id>` endpoint
  - `pcm_16000` raw PCM output
  - 16 kHz, 16-bit, mono, little-endian audio
  - streaming response consumption is supported
- Remaining implementation-time checks:
  - exact error response body shape for non-2xx responses
  - whether preview endpoint has rate-limit response details worth preserving in `vendor_info`
  - whether `speechmatics-tts` adds value over direct `httpx`

## 5a) Prior-art check
- Existing `speechmatics_asr_python` provides package naming, API key naming, redaction, and manifest patterns, but not the TTS transport.
- Local git history did not surface an obvious Ben Weekes Speechmatics TTS implementation. If more history is available in another remote/branch, inspect it before implementation.
- For concrete implementation structure, use recent HTTP TTS providers:
  - `openai_tts2_python`
  - `groq_tts_python`
  - `rime_http_tts`

## 6) Edge behavior to preserve (minimal + production-safe)
- Required-key failure must fail fast and report `FATAL_ERROR`.
- Keep `dump` support and redaction consistent with `speechmatics_asr_python` / ASR/TTS conventions.
- Preserve request state during interrupts:
  - if `text_input_end` arrives after `flush`, do not emit stale completion.
  - ensure `tts_audio_end` reason is mapped correctly.
- Emit metrics with non-breaking timestamps where supported.

## 7) Validation plan (after approval)
- Standalone extension tests:
  - `cd ai_agents && task test-extension-no-install EXTENSION=agents/ten_packages/extension/speechmatics_tts_python`
- Guarder:
  - `cd ai_agents && task tts-guarder-test EXTENSION=speechmatics_tts_python`
  - If the harness enforces different sample rates, run with sample-rate comparison disabled because Speechmatics documents only `pcm_16000`/`wav_16000`.
- Formatting/lint:
  - `cd ai_agents && task format` or `task check`
- Local Docker integration smoke (requires user-provided Speechmatics API key):
  - Ask the user to configure `SPEECHMATICS_API_KEY` in the local TEN agent environment before running live-provider tests.
  - Use the repo's Docker flow instead of host-local runtime execution.
  - From the relevant Docker/app location, start the container stack with `docker compose up -d`.
  - After container start or env changes, reinstall Python dependencies inside the container as required by this repo's setup docs.
  - Run the example install:
    - `docker exec ten_agent_dev bash -c "cd /app/agents/examples/voice-assistant && task install"`
  - Run the example:
    - `docker exec -d ten_agent_dev bash -c "cd /app/agents/examples/voice-assistant && task run > /tmp/task_run.log 2>&1"`
  - Confirm server health:
    - `curl -s http://localhost:8080/health`
  - Confirm the graph is available:
    - `curl -s http://localhost:8080/graphs`
    - verify `voice_assistant_speechmatics_tts` appears if that graph was added
  - Inspect logs for startup/config errors:
    - `docker exec ten_agent_dev tail -n 200 /tmp/task_run.log`
    - specifically check for `speechmatics_tts_python`, `config:`, `vendor_error`, `tts_audio_start`, `tts_audio_end`, and auth/rate-limit failures.
  - If logs are noisy or binary-looking, inspect printable strings:
    - `docker exec ten_agent_dev bash -c "strings /tmp/task_run.log | tail -n 200"`
  - Exercise the graph through the playground/API once the user has configured the API key, then re-check `/tmp/task_run.log` for TTFB metrics, streamed audio chunks, and clean request completion.
- Non-Docker integration smoke (only if Docker is unavailable):
  - `cd ai_agents/agents/examples/voice-assistant && task install`
  - `cd ai_agents/agents/examples/voice-assistant && task run`
  - run voice assistant graph in browser and verify speech-in/out.

## 8) Open decisions before coding
1. Decide whether to add Speechmatics TTS to only `voice-assistant` or additional sample graphs.
2. Decide whether to use direct `httpx` (recommended) or the preview `speechmatics-tts` package after checking maintenance/API fit.
3. Confirm whether to preserve `SPEECHMATICS_API_KEY` for both ASR and TTS (recommended for consistency) or introduce `SPEECHMATICS_TTS_KEY`.
