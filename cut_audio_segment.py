"""
Apgriez konkretu audio fragmentu no liela faila.
Pielago START_MINUTE un DURATION_MINUTES, lai atrastu vajadzigo gabalu.
"""
from pathlib import Path
import subprocess

# Mainot sos parametrus, var izveidot citus testa fragmentus
START_MINUTE = 40       # No kuras minutes sakt
DURATION_MINUTES = 5    # Cik minutes apgriezt
SOURCE_NAME = "vairakiRunataji.ogg"  # Avota fails

# Atrod mapes
BASE_DIR = Path(__file__).resolve().parents[1]

# Avots var but vai nu audio mape, vai projekta sakne
source_candidates = [
    BASE_DIR / "audio" / SOURCE_NAME,
    BASE_DIR / SOURCE_NAME,
]

source = None
for candidate in source_candidates:
    if candidate.exists():
        source = candidate
        break

if source is None:
    print(f"Kluda: nav atrasts fails {SOURCE_NAME}")
    print(f"Mekleju seit: {[str(c) for c in source_candidates]}")
    exit(1)

# Veido jauna faila nosaukumu
output_dir = BASE_DIR / "audio"
output = output_dir / f"TEST_min{START_MINUTE}-{START_MINUTE + DURATION_MINUTES}_{SOURCE_NAME}"

print(f"Avots: {source}")
print(f"Apgriez no {START_MINUTE}. minutes uz {DURATION_MINUTES} minutem...")
print(f"Saglabas ka: {output.name}")

# ffmpeg komanda - apgriez no konkretas pozicijas
cmd = [
    "ffmpeg",
    "-y",
    "-i", str(source),
    "-ss", f"{START_MINUTE * 60}",        # sakuma pozicija sekundes
    "-t", f"{DURATION_MINUTES * 60}",     # ilgums sekundes
    "-c", "copy",                          # bez parkodesanas (atrak)
    str(output)
]

try:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nGatavs! Testa fails: {output.name}")
except subprocess.CalledProcessError as e:
    print(f"Kluda ffmpeg darbiba: {e}")
except FileNotFoundError:
    print("Kluda: ffmpeg nav atrasts.")