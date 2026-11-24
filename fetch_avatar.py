"""Download Roblox's official blocky character for local rendering."""
import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

TARGET = Path(__file__).resolve().parent / "assets" / "BlockyCharacter.fbx"
URL = ("https://media.githubusercontent.com/media/Roblox/creator-docs/main/content/en-us/"
       "assets/avatar/dynamic-heads/reference-files/BlockyCharacter.fbx")
DIGEST = "3bce4f161bc9b3825d4580e756c0a2da3b737cfbff1c2d41f47405aabe32803a"


MARKET_ASSETS = {
    "NatureGirl": ("NatureArcherGirl", "NatureArcherGirl/Blender/NatureArcherGirl_WithClothing.fbx",
                   "581c16738feda7baff0fce45aaadfc86feb004d1f38795d037471aa5cf2ba384"),
    "StylishMale": ("StylizedMaleWithClothing", "StylizedMaleWithClothing/Blender/LC_StylizedMale_WithClothing.fbx",
                   "389286ea7045d74aab928e535fb74674c47a18033cd4d1a8a05a87c522bd1929"),
}


def download(url, limit, digest):
    with urlopen(url, timeout=30) as source:
        data = source.read(limit + 1)
    if len(data) > limit or sha256(data).hexdigest() != digest:
        raise ValueError("Roblox avatar download failed the expected file check")
    return data


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".download")
    temporary.write_bytes(data)
    temporary.replace(path)
    print(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", action="store_true", help="Also download Nature Girl and Stylish Male")
    args = parser.parse_args()
    save(TARGET, download(URL, 5_000_000, DIGEST))
    if args.market:
        art_url = URL.split("/assets/", 1)[0] + "/assets/art/reference-files"
        for name, (archive_name, member, digest) in MARKET_ASSETS.items():
            archive = download(f"{art_url}/{archive_name}.zip", 300_000_000, digest)
            with ZipFile(BytesIO(archive)) as bundle:
                save(TARGET.with_name(f"{name}.fbx"), bundle.read(member))



if __name__ == "__main__":
    main()
