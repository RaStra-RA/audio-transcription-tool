"""
Multi-valodu transkripcija ar fizisku audio sadalisanu.
Katram gabalam atseviski atpazis valodu, tad transkribe ar piespiestu valodu.
"""
from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = BASE_DIR / "audio"
OUT_DIR = BASE_DIR / "text"

SUPPORTED_EXTENSIONS = {".mp3", ".ogg", ".opus", ".wav", ".mp4", ".m4a", ".aac", ".flac"}

# Parametri
CHUNK_SECONDS = 30  # cik sekunzu garums katram gabalinam


def to_wav(src: Path, dst: Path) -> bool:
    """Konverte audio uz WAV formatu (mono, 16kHz)."""
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Kluda konvertejot: {e}")
        return False


def get_audio_duration(wav_file: Path) -> float:
    """Atgriez audio garumu sekundes."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(wav_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_chunk(src: Path, dst: Path, start: float, duration: float) -> bool:
    """Izgriez audio gabalu no start uz duration sekundem."""
    cmd = ["ffmpeg", "-y", "-i", str(src),
           "-ss", str(start), "-t", str(duration),
           "-c", "copy", str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
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
    print("Modelis ieladets!\n")

    for audio in audio_files:
        print(f"{'='*60}")
        print(f"Apstrada: {audio.name}")
        print(f"{'='*60}")

        out_txt = OUT_DIR / f"{audio.stem}_smart.txt"
        out_json = OUT_DIR / f"{audio.stem}_smart.json"
        wav_file = OUT_DIR / f"{audio.stem}_temp.wav"
        chunk_dir = OUT_DIR / f"{audio.stem}_chunks"
        chunk_dir.mkdir(exist_ok=True)

        try:
            # Solis 1: konverte uz WAV
            print("Konvertē uz WAV...")
            if not to_wav(audio, wav_file):
                continue

            duration = get_audio_duration(wav_file)
            print(f"Audio garums: {format_timestamp(duration)}\n")

            # Solis 2: sadala gabalinos
            num_chunks = int(duration // CHUNK_SECONDS) + (1 if duration % CHUNK_SECONDS > 0 else 0)
            print(f"Sadala {num_chunks} gabalinos pa {CHUNK_SECONDS} sek...\n")

            all_segments = []

            for i in range(num_chunks):
                chunk_start = i * CHUNK_SECONDS
                chunk_duration = min(CHUNK_SECONDS, duration - chunk_start)

                if chunk_duration < 1:  # parak iss
                    continue

                chunk_file = chunk_dir / f"chunk_{i:04d}.wav"

                # Izgriez gabalinu
                if not extract_chunk(wav_file, chunk_file, chunk_start, chunk_duration):
                    print(f"Kluda izgriest gabalu {i}")
                    continue

                # Solis 3a: ATPAZIST VALODU katram gabalam atseviski
                segments, info = model.transcribe(
                    str(chunk_file),
                    language=None,
                    beam_size=1,
                    vad_filter=True,
                )

                detected_lang = info.language
                lang_prob = info.language_probability

                # Solis 3b: AUTO-KOREKCIJA - jaunaja valoda atpaziniana
                # Ja zema parliecība un atpazis tuvu slavu valodu, piespiediam krievu
                slavic_neighbors = ('uk', 'be', 'bg', 'mk', 'sr', 'hr')
                if lang_prob < 0.75 and detected_lang in slavic_neighbors:
                    print(f"   AUTO-KOREKCIJA: {detected_lang}({lang_prob:.0%}) -> ru")
                    detected_lang = 'ru'

                    # Transkribē vel reizi ar piespiestu krievu valodu
                    segments, info = model.transcribe(
                        str(chunk_file),
                        language='ru',  # PIESPIEDU
                        beam_size=5,    # labaka kvalitate
                        vad_filter=True,
                    )

                # Pielieto tikai ja parliecība pietiekami liela
                if lang_prob < 0.4 and detected_lang not in ('lv', 'ru', 'en'):
                    detected_lang = "unknown"

                segments_list = list(segments)

                start_str = format_timestamp(chunk_start)
                print(f"[{start_str}] Atpazita valoda: {detected_lang} ({lang_prob:.0%})")

                for seg in segments_list:
                    text = seg.text.strip()
                    if not text:
                        continue

                    # Pielieto reali laika kodi
                    real_start = chunk_start + seg.start
                    real_end = chunk_start + seg.end

                    seg_data = {
                        "start": real_start,
                        "end": real_end,
                        "text": text,
                        "language": detected_lang,
                    }
                    all_segments.append(seg_data)

                    print(f"   ({detected_lang}) {text[:80]}")

                # Dzes pagaidu gabalu
                chunk_file.unlink()

            # Saglaba rezultatus
            print(f"\nKopa: {len(all_segments)} segmenti")

            with out_txt.open("w", encoding="utf-8") as f:
                for s in all_segments:
                    start_str = format_timestamp(s['start'])
                    end_str = format_timestamp(s['end'])
                    f.write(f"[{start_str} - {end_str}] ({s['language']}) {s['text']}\n")

            with out_json.open("w", encoding="utf-8") as f:
                json.dump({
                    "source": audio.name,
                    "chunks": num_chunks,
                    "segments": all_segments
                }, f, ensure_ascii=False, indent=2)

            print(f"Saglabats: {out_txt.name}")

        except Exception as e:
            print(f"Kluda: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if wav_file.exists():
                wav_file.unlink()
            # Dzes pagaidu chunks mapi
            try:
                chunk_dir.rmdir()
            except OSError:
                pass

    print("\nViss pabeigts.")


if __name__ == "__main__":
    main()