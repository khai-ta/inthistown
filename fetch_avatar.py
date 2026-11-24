"""Download Roblox's official blocky character for local rendering."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

TARGET = Path(__file__).resolve().parent / "assets" / "BlockyCharacter.fbx"
URL = ("https://media.githubusercontent.com/media/Roblox/creator-docs/main/content/en-us/"
       "assets/avatar/dynamic-heads/reference-files/BlockyCharacter.fbx")
DIGEST = "3bce4f161bc9b3825d4580e756c0a2da3b737cfbff1c2d41f47405aabe32803a"


def main():
    with urlopen(URL, timeout=30) as source:
        data = source.read(5_000_000)
    if sha256(data).hexdigest() != DIGEST:
        raise ValueError("Roblox avatar download does not match the expected FBX")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temporary = TARGET.with_suffix(".download")
    temporary.write_bytes(data)
    temporary.replace(TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()
