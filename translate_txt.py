from pathlib import Path
import argostranslate.translate as tr

def main():
    base = Path(__file__).resolve().parents[1]
    text_dir = base / "text"

    inp = next(text_dir.glob("*.txt"))
    out = inp.with_suffix(".lv.txt")

    ru = inp.read_text(encoding="utf-8")
    en = tr.translate(ru, "ru", "en")
    lv = tr.translate(en, "en", "lv")

    out.write_text(lv, encoding="utf-8")
    print("OK:", out)

if __name__ == "__main__":
    main()
