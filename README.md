# 🎙️ Audio Transcription Tool

Python-based transcription tool with speaker diarization — identifies who is speaking, assigns each speaker a unique color, and exports results with timestamps to Word (.docx) and SRT formats. Supports Latvian, Russian, and English.

## ✨ Features

- 🎨 Color-coded speakers — each speaker gets a unique color
- ⏱️ Timestamps for every segment
- 👥 Speaker diarization (who said what)
- 🌍 Multilingual: Latvian, Russian, English
- 📄 Export to Word (.docx) and SRT subtitle format
- ✂️ Audio cutting tools included

## 🛠️ Scripts

| File | Description |
|------|-------------|
| `transcribe_speakers.py` | Main script — transcription with speaker diarization and color coding |
| `transcribe_smart.py` | Smart transcription with enhanced features |
| `transcribe_multilang.py` | Multilingual transcription (LV, RU, EN) |
| `export_transcript.py` | Export to Word (.docx) and SRT format |
| `cut_audio.py` | Cut audio files |
| `cut_audio_segment.py` | Cut specific audio segments |
| `translate_txt.py` | Translate transcribed text |
| `install_argos.py` | Install Argos Translate |
| `test_diarization.py` | Test diarization setup |

## ⚙️ Requirements

- Python 3.9+
- [Whisper](https://github.com/openai/whisper)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
- HuggingFace token (for diarization)
- `pip install openai-whisper pyannote.audio python-docx`

## 🔑 Setup

1. Create a `.env` file with your HuggingFace token:
2. HF_TOKEN=your_token_here
2. Run `install_argos.py` for translation support
3. Run `transcribe_speakers.py` to start

## 👩‍💻 Author
Built by [RaStra](https://github.com/RaStra-RA) · Available for custom AI tools on [Fiverr](https://www.fiverr.com/ra_stra)
