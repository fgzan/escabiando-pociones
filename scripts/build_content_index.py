"""
Junta todos los archivos individuales de content/reviews/*.json y
content/noticias/*.json en dos archivos índice (content/reviews.json y
content/noticias.json) que son los que la web realmente lee.

Se corre solo, disparado por el GitHub Action en
.github/workflows/build-index.yml, cada vez que el panel guarda una
review o noticia nueva. No hace falta correrlo a mano.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(folder_name, index_name):
    folder = ROOT / "content" / folder_name
    items = []

    if folder.exists():
        for file in sorted(folder.glob("*.json")):
            with open(file, encoding="utf-8") as fh:
                data = json.load(fh)
            data["slug"] = file.stem
            items.append(data)

    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    out_path = ROOT / "content" / f"{index_name}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"{out_path}: {len(items)} elemento(s)")


if __name__ == "__main__":
    build("reviews", "reviews")
    build("noticias", "noticias")
