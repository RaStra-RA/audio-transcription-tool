"""
Apgriez pirmo audio failu mapē 'audio' uz īsu testa versiju.
Oriģinālais fails paliek neskarts.
"""
from pathlib import Path
import subprocess

# Cik minūtes apgriezt? Mainot šo skaitli, var izveidot citas garas testa versijas.
TEST_MINUTES = 5

# Atrod mapes
BASE_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = BASE_DIR / "audio"

# Atrod pirmo audio failu
SUPPORTED = {".mp3", ".wav", ".m4a", ".ogg", ".opus", ".mp4", ".aac", ".flac"}
audio_files = [f for f in AUDIO_DIR.iterdir() if f.suffix.lower() in SUPPORTED]

if not audio_files:
    print(f"Kluda: nav audio failu mape {AUDIO_DIR}")
    exit(1)

# Sakaarto failus pec nosaukuma, lai vienmer pirmais ir tas pats
audio_files.sort()
source = audio_files[0]

# Veido jauna faila nosaukumu
output = AUDIO_DIR / f"TEST_{TEST_MINUTES}min_{source.name}"

print(f"Avots: {source.name}")
print(f"Apgriez pirmas {TEST_MINUTES} minutes...")
print(f"Saglabas ka: {output.name}")

# ffmpeg komanda - apgriez bez parkodesanas (atri!)
cmd = [
    "ffmpeg",
    "-y",                    # parraksta, ja jau eksiste
    "-i", str(source),       # ievades fails
    "-t", f"{TEST_MINUTES * 60}",  # ilgums sekundes
    "-c", "copy",            # kopee bez parkodesanas (atrak)
    str(output)
]

try:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nGatavs! Testa fails saglabats: {output.name}")
    print(f"Tagad var palaist test_diarization.py")
except subprocess.CalledProcessError as e:
    print(f"Kluda ffmpeg darbiba: {e}")
except FileNotFoundError:
    print("Kluda: ffmpeg nav atrasts. Parbaudi instalaciju.")