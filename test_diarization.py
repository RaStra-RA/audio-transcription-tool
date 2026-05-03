from pathlib import Path
import os
from dotenv import load_dotenv
from pyannote.audio import Pipeline

# Load token from .env
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    print("ERROR: HF_TOKEN not found in .env file!")
    exit(1)

# Find first audio file in audio folder
AUDIO_DIR = BASE_DIR / "audio"
audio_files = list(AUDIO_DIR.glob("*"))
audio_files = [f for f in audio_files if f.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".opus", ".mp4", ".aac", ".flac"}]

if not audio_files:
    print(f"ERROR: no audio files found in {AUDIO_DIR}")
    exit(1)

audio_files.sort()
audio_file = audio_files[0]
print(f"Processing file: {audio_file.name}")

# Load model (first time downloads ~500 MB)
print("\nLoading speaker diarization model...")
print("(first run may take 5-10 min to download model)")

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HF_TOKEN
)
print("Model loaded!")

# Run diarization
print(f"\nProcessing {audio_file.name}...")
print("(this may take several minutes depending on audio length)")

diarization = pipeline(str(audio_file))

# Print results
print("\n" + "="*60)
print("RESULTS:")
print("="*60)

for turn, _, speaker in diarization.itertracks(yield_label=True):
    start = f"{int(turn.start // 60):02}:{int(turn.start % 60):02}"
    end = f"{int(turn.end // 60):02}:{int(turn.end % 60):02}"
    print(f"  {start} - {end}  ->  {speaker}")

print("\nDone!")