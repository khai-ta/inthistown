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
    "Fish-Person": "ee71219663b8c965b2c997fff8b54054bd318eaeab80ec7798c9a7302542dcf8",
    "GoblinCharacter": "65642c668b69a15bcab36af96f86f6513fa368bd78c83e7a67899415f5024a49",
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
    parser.add_argument("--market", action="store_true", help="Also download Fish Person and Goblin")
    args = parser.parse_args()
    save(TARGET, download(URL, 5_000_000, DIGEST))
    if args.market:
        for name, digest in MARKET_ASSETS.items():
            archive = download(URL.rsplit("/", 1)[0] + f"/{name}.zip", 25_000_000, digest)
            with ZipFile(BytesIO(archive)) as bundle:
                save(TARGET.with_name(f"{name}.fbx"), bundle.read(f"{name}/{name}.fbx"))


if __name__ == "__main__":
    main()
