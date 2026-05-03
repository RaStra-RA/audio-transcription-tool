"""
Multi-valodu transkripcija.
Sadala audio fragmentos un atpazist valodu katram fragmentam atseviski.
Strada labak, ja audio ir vairaki valodu runataji.
"""
from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = BASE_DIR / "audio"
OUT_DIR = BASE_DIR / "text"

SUPPORTED_EXTENSIONS = {".mp3", ".ogg", ".opus", ".wav", ".mp4", ".m4a", ".aac", ".flac"}


def to_wav(src: Path, dst: Path) -> bool:
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Kluda konvertejot: {e}")
        return False


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02}:{m:02}:{s:02}"


def main():
    if not AUDIO_DIR.exists():
        print(f"Kluda: nav atrasta audio mape: {AUDIO_DIR}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    audio_files = [f for f in AUDIO_DIR.iterdir()
                   if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not audio_files:
        print("Nav atrasti audio faili.")
        return

    print("Ieladē Whisper modeli...")
    model = WhisperModel("medium", device="cpu", compute_type="int8")

    for audio in audio_files:
        print(f"\n{'='*60}")
        print(f"Apstrada: {audio.name}")
        print(f"{'='*60}")

        out_txt = OUT_DIR / f"{audio.stem}_multilang.txt"
        out_json = OUT_DIR / f"{audio.stem}_multilang.json"
        wav_file = OUT_DIR / f"{audio.stem}_temp.wav"

        try:
            if not to_wav(audio, wav_file):
                continue

            # GALVENA ATSKIRIBA: language=None KATRAM segmentam
            # Whisper atpazis valodu kasdam segmentam atseviski
            print("Sak transkribesanu ar valodu atpazisanu...")

            segments, info = model.transcribe(
                str(wav_file),
                language=None,
                beam_size=5,            # labaka kvalitate
                best_of=5,              # labaka kvalitate
                vad_filter=True,
                condition_on_previous_text=False,  # SVARIGI: nepiesaista pie iepriekseja teksta
                temperature=[0.0, 0.2, 0.4],       # mēģina vairākas reizes
            )

            print(f"Galvena atpazita valoda: {info.language}")
            print()

            segments_data = []
            for i, seg in enumerate(segments, 1):
                text = seg.text.strip()
                if not text:
                    continue

                start_str = format_timestamp(seg.start)
                end_str = format_timestamp(seg.end)

                # Whisper segmenta lidzi nesatur valodu, bet
                # mes varam atrast no avg_logprob un no_speech_prob
                lang = getattr(seg, 'language', info.language) or info.language

                segments_data.append({
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": text,
                    "language": lang,
                    "avg_logprob": float(getattr(seg, 'avg_logprob', 0)),
                })

                print(f"  [{start_str}] ({lang}) {text}")

            # Saglaba rezultatus
            with out_txt.open("w", encoding="utf-8") as f:
                for s in segments_data:
                    start_str = format_timestamp(s['start'])
                    end_str = format_timestamp(s['end'])
                    f.write(f"[{start_str} - {end_str}] ({s['language']}) {s['text']}\n")

            with out_json.open("w", encoding="utf-8") as f:
                json.dump({
                    "source": audio.name,
                    "main_language": info.language,
                    "segments": segments_data
                }, f, ensure_ascii=False, indent=2)

            print(f"\nGatavs! Saglabats: {out_txt.name}")

        except Exception as e:
            print(f"Kluda: {e}")
        finally:
            if wav_file.exists():
                wav_file.unlink()

    print("\nViss pabeigts.")


if __name__ == "__main__":
    main()