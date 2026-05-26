# Speechmatics TTS Extension

HTTP streaming text-to-speech extension for Speechmatics TTS.

## Configuration

```json
{
  "dump": false,
  "dump_path": "./",
  "params": {
    "api_key": "${env:SPEECHMATICS_API_KEY|}",
    "voice": "sarah",
    "output_format": "pcm_16000",
    "base_url": "https://preview.tts.speechmatics.com",
    "sample_rate": 16000
  }
}
```

## Parameters

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `params.api_key` | yes | `${env:SPEECHMATICS_API_KEY|}` | Speechmatics API key used as a bearer token. |
| `params.voice` | no | `sarah` | Voice ID. Current documented voices include `sarah`, `theo`, `megan`, and `jack`. |
| `params.output_format` | no | `pcm_16000` | Raw PCM output format. This extension supports `pcm_16000`. |
| `params.base_url` | no | `https://preview.tts.speechmatics.com` | Speechmatics TTS base URL. |
| `params.sample_rate` | no | `16000` | Output sample rate. Speechmatics currently documents 16 kHz TTS output. |
| `dump` | no | `false` | Enable PCM dump for debugging. |
| `dump_path` | no | `./` | Dump output location. |

## Audio format

The extension requests `pcm_16000` and emits raw PCM:

- 16 kHz
- 16-bit signed integer
- mono
- little-endian

## Example graph node

```json
{
  "type": "extension",
  "name": "tts",
  "addon": "speechmatics_tts_python",
  "extension_group": "tts",
  "property": {
    "dump": false,
    "dump_path": "./",
    "params": {
      "api_key": "${env:SPEECHMATICS_API_KEY|}",
      "voice": "sarah",
      "output_format": "pcm_16000",
      "sample_rate": 16000
    }
  }
}
```
