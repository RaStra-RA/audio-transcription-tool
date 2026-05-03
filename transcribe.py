from pathlib import Path
import subprocess
import json
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR.parent / "audio"
OUT_DIR = BASE_DIR.parent / "text"

SUPPORTED_EXTENSIONS = {".mp3", ".ogg", ".opus", ".wav", ".mp4", ".m4a", ".aac", ".flac"}


def to_wav(src: Path, dst: Path) -> bool:
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", "16000",
        str(dst)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"Kļūda konvertējot failu: {src.name}")
        return False
    except FileNotFoundError:
        print("Kļūda: ffmpeg nav atrasts. Pārbaudi, vai ffmpeg ir uzinstalēts un pievienots PATH.")
        return False


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"


def save_plain_text(output_file: Path, segments_data: list[dict]) -> None:
    lines = [seg["text"] for seg in segments_data if seg["text"]]
    output_file.write_text("\n".join(lines), encoding="utf-8")


def save_timestamped_text(output_file: Path, segments_data: list[dict]) -> None:
    lines = []
    for seg in segments_data:
        if seg["text"]:
            lines.append(f"{format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}  {seg['text']}")
    output_file.write_text("\n".join(lines), encoding="utf-8")


def main():
    if not AUDIO_DIR.exists():
        print(f"Kļūda: audio mape nav atrasta: {AUDIO_DIR}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    audio_files = [f for f in AUDIO_DIR.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not audio_files:
        print("Nav atrasti audio/video faili apstrādei.")
        return

    print("Ielādē modeli...")
    try:
        model = WhisperModel(
            "medium",
            device="cpu",
            compute_type="int8"
        )
    except Exception as e:
        print(f"Kļūda ielādējot modeli: {e}")
        return

    for audio in audio_files:
        print(f"\nApstrādā: {audio.name}")

        txt_file = OUT_DIR / f"{audio.stem}.txt"
        json_file = OUT_DIR / f"{audio.stem}.json"
        timed_txt_file = OUT_DIR / f"{audio.stem}_timestamps.txt"
        wav_file = OUT_DIR / f"{audio.stem}.wav"

        try:
            if txt_file.exists() and json_file.exists():
                print(f"Izlaiž, jo jau apstrādāts: {audio.name}")
                continue

            converted = to_wav(audio, wav_file)
            if not converted:
                continue

            print("Sāk transkribēšanu...")

            segments, info = model.transcribe(
                str(wav_file),
                language=None,
                beam_size=1,
                best_of=1,
                vad_filter=True,
                condition_on_previous_text=False
            )

            print(f"Atpazītā valoda: {getattr(info, 'language', 'nav zināma')}")

            segments_data = []
            for i, s in enumerate(segments, 1):
                text = s.text.strip()
                print(f"Segments {i}: {format_timestamp(float(s.start))} - {format_timestamp(float(s.end))}")
                if text:
                    segments_data.append({
                        "start": float(s.start),
                        "end": float(s.end),
                        "text": text
                    })

            save_plain_text(txt_file, segments_data)
            save_timestamped_text(timed_txt_file, segments_data)

            output_json = {
                "source_file": audio.name,
                "detected_language": getattr(info, "language", None),
                "language_probability": getattr(info, "language_probability", None),
                "segments": segments_data
            }

            json_file.write_text(
                json.dumps(output_json, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"Pabeigts: {audio.name}")

        except Exception as e:
            print(f"Kļūda apstrādājot {audio.name}: {e}")

        finally:
            if wav_file.exists():
                wav_file.unlink()

    print("\nViss pabeigts.")


if __name__ == "__main__":
    main()