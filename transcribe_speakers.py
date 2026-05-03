"""
Multi-valodu transkripcija ar runataju atpazisanu.
Apvieno Whisper transkripciju ar pyannote runataju atpazisanu.
"""
from pathlib import Path
import subprocess
import json
import os
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = BASE_DIR / "audio"
OUT_DIR = BASE_DIR / "text"

SUPPORTED_EXTENSIONS = {".mp3", ".ogg", ".opus", ".wav", ".mp4", ".m4a", ".aac", ".flac"}
CHUNK_SECONDS = 30


def to_wav(src: Path, dst: Path) -> bool:
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Kluda konvertejot: {e}")
        return False


def get_audio_duration(wav_file: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(wav_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract_chunk(src: Path, dst: Path, start: float, duration: float) -> bool:
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


def find_speaker_for_segment(seg_start, seg_end, speaker_turns):
    """
    Atrod, kurs runataajs runaja segmenta vidu.
    speaker_turns: saraksts ar (start, end, speaker)
    """
    seg_middle = (seg_start + seg_end) / 2

    # Mekle pirmo turn, kuras laika ir segmenta vidus
    for turn_start, turn_end, speaker in speaker_turns:
        if turn_start <= seg_middle <= turn_end:
            return speaker

    # Ja neatrod, mekle tuvako
    closest_speaker = "UNKNOWN"
    closest_distance = float('inf')
    for turn_start, turn_end, speaker in speaker_turns:
        # Distance lidz tuvakajai robezai
        if seg_middle < turn_start:
            distance = turn_start - seg_middle
        elif seg_middle > turn_end:
            distance = seg_middle - turn_end
        else:
            distance = 0

        if distance < closest_distance:
            closest_distance = distance
            closest_speaker = speaker

    return closest_speaker


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

    # Ielādē tokenu
    load_dotenv(BASE_DIR / ".env")
    HF_TOKEN = os.getenv("HF_TOKEN")
    if not HF_TOKEN:
        print("Kluda: HF_TOKEN nav atrasts .env faila!")
        return

    # Ielādē pyannote modeli
    print("Ielādē pyannote modeli...")
    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HF_TOKEN
    )
    print("Pyannote ieladets!")

    # Ielādē Whisper modeli
    print("Ielādē Whisper modeli...")
    whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
    print("Whisper ieladets!\n")

    for audio in audio_files:
        print(f"{'='*60}")
        print(f"Apstrada: {audio.name}")
        print(f"{'='*60}")

        out_txt = OUT_DIR / f"{audio.stem}_speakers.txt"
        out_json = OUT_DIR / f"{audio.stem}_speakers.json"
        wav_file = OUT_DIR / f"{audio.stem}_temp.wav"
        chunk_dir = OUT_DIR / f"{audio.stem}_chunks"
        chunk_dir.mkdir(exist_ok=True)

        try:
            # Solis 1: konverte uz WAV
            print("Konvertē uz WAV...")
            if not to_wav(audio, wav_file):
                continue

            duration = get_audio_duration(wav_file)
            print(f"Audio garums: {format_timestamp(duration)}")

            # Solis 2: PYANNOTE - atpazis runatajus
            print("\nPalaiž runatāju atpazisanu (var aiznemt vairakas minutes)...")

            # Var piespiest skritu runataju skaitu, ja zinams
            # Vienkarsi raksta filea: vairakiRunataji_speakers.txt
            # ar tekstu "num_speakers=2" vai "min=2,max=4"
            speakers_config_file = AUDIO_DIR / f"{audio.stem}_speakers.txt"
            diarization_kwargs = {}

            if speakers_config_file.exists():
                config = speakers_config_file.read_text().strip()
                if config.startswith("num_speakers="):
                    n = int(config.split("=")[1])
                    diarization_kwargs['num_speakers'] = n
                    print(f"Piespiediam {n} runatajus (no config faila)")
                elif "min=" in config and "max=" in config:
                    parts = dict(p.split("=") for p in config.split(","))
                    diarization_kwargs['min_speakers'] = int(parts['min'])
                    diarization_kwargs['max_speakers'] = int(parts['max'])
                    print(f"Diapazons: {parts['min']}-{parts['max']} runataji (no config)")

            diarization = diarization_pipeline(str(wav_file), **diarization_kwargs)

            speaker_turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_turns.append((turn.start, turn.end, speaker))

            print(f"Atrasti {len(set(s for _,_,s in speaker_turns))} runataji")
            print(f"Kopa segmenti: {len(speaker_turns)}\n")

            # Solis 3: WHISPER ar valodu atpazisanu
            print("Sak transkribesanu...")
            num_chunks = int(duration // CHUNK_SECONDS) + (1 if duration % CHUNK_SECONDS > 0 else 0)

            all_segments = []

            for i in range(num_chunks):
                chunk_start = i * CHUNK_SECONDS
                chunk_duration = min(CHUNK_SECONDS, duration - chunk_start)

                if chunk_duration < 1:
                    continue

                chunk_file = chunk_dir / f"chunk_{i:04d}.wav"

                if not extract_chunk(wav_file, chunk_file, chunk_start, chunk_duration):
                    continue

                # Atpazis valodu
                segments, info = whisper_model.transcribe(
                    str(chunk_file),
                    language=None,
                    beam_size=1,
                    vad_filter=True,
                )

                detected_lang = info.language
                lang_prob = info.language_probability

                # Auto-korekcija slavu valodam
                slavic_neighbors = ('uk', 'be', 'bg', 'mk', 'sr', 'hr')
                if lang_prob < 0.75 and detected_lang in slavic_neighbors:
                    detected_lang = 'ru'
                    segments, info = whisper_model.transcribe(
                        str(chunk_file),
                        language='ru',
                        beam_size=5,
                        vad_filter=True,
                    )

                if lang_prob < 0.4 and detected_lang not in ('lv', 'ru', 'en'):
                    detected_lang = "unknown"

                segments_list = list(segments)

                start_str = format_timestamp(chunk_start)
                print(f"[{start_str}] Valoda: {detected_lang}")

                for seg in segments_list:
                    text = seg.text.strip()
                    if not text:
                        continue

                    real_start = chunk_start + seg.start
                    real_end = chunk_start + seg.end

                    # Atrod runātāju
                    speaker = find_speaker_for_segment(real_start, real_end, speaker_turns)

                    seg_data = {
                        "start": real_start,
                        "end": real_end,
                        "text": text,
                        "language": detected_lang,
                        "speaker": speaker,
                    }
                    all_segments.append(seg_data)

                    print(f"   {speaker} ({detected_lang}) {text[:70]}")

                chunk_file.unlink()

            # Saglabā rezultatus
            print(f"\nKopa: {len(all_segments)} segmenti")

            with out_txt.open("w", encoding="utf-8") as f:
                for s in all_segments:
                    start_str = format_timestamp(s['start'])
                    end_str = format_timestamp(s['end'])
                    f.write(f"[{start_str} - {end_str}] {s['speaker']} ({s['language']}) {s['text']}\n")

            with out_json.open("w", encoding="utf-8") as f:
                json.dump({
                    "source": audio.name,
                    "duration": duration,
                    "speakers": list(set(s for _,_,s in speaker_turns)),
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
            try:
                chunk_dir.rmdir()
            except OSError:
                pass

    print("\nViss pabeigts!")


if __name__ == "__main__":
    main()