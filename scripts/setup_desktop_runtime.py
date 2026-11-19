"""Install a pinned, checksum-verified official llama.cpp Windows CUDA runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TAG = "b12478"
MODEL = "models/deployment/gemma_v5_3epochs_20261117/kanglish-gemma-3-1b-it-Q4_K_M.gguf"
MODEL_SHA = "12d2c4c56b583d58cea93ca0201516d873d5db389eb8690a26ea3cf3c07f0945"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def install(tag=TAG):
    directory = ROOT / ".tools" / "desktop" / tag
    directory.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{tag}",
        headers={"User-Agent": "Kanglish-desktop-setup"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    names = [f"llama-{tag}-bin-win-cuda-13.5-x64.zip", "cudart-llama-bin-win-cuda-13.5-x64.zip"]
    installed = []
    for name in names:
        asset = next(a for a in release["assets"] if a["name"] == name)
        expected = asset.get("digest", "")
        if not expected.startswith("sha256:"):
            raise ValueError(f"Official SHA-256 missing for {name}")
        archive = directory / name
        if not archive.exists() or digest(archive) != expected.split(":", 1)[1]:
            print(f"Downloading {name} ({asset['size'] / 1024**2:.0f} MiB)...", flush=True)
            partial = archive.with_suffix(".partial")
            with urllib.request.urlopen(asset["browser_download_url"], timeout=60) as response, partial.open("wb") as output:
                while block := response.read(4 * 1024 * 1024):
                    output.write(block)
            if digest(partial) != expected.split(":", 1)[1]:
                raise ValueError(f"Checksum mismatch for {name}; file kept for inspection")
            partial.replace(archive)
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                target = (directory / member.filename).resolve()
                if not target.is_relative_to(directory.resolve()):
                    raise ValueError("Runtime archive contains an unsafe path")
            source.extractall(directory)
        installed.append({"name": name, "sha256": digest(archive), "url": asset["browser_download_url"]})
        print(f"Verified and installed {name}", flush=True)
    binary = next(directory.rglob("llama-server.exe"))
    model = ROOT / MODEL
    if not model.is_file() or digest(model) != MODEL_SHA:
        raise ValueError("Expected local Gemma export missing or checksum changed")
    manifest = {"tag": tag, "release_url": release["html_url"], "assets": installed,
                "binary": str(binary.relative_to(ROOT)), "binary_sha256": digest(binary)}
    (directory / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    config = ROOT / "configs" / "desktop.local.json"
    if not config.exists():
        config.write_text(json.dumps({"binary": str(binary.relative_to(ROOT)), "model": MODEL,
            "model_sha256": MODEL_SHA, "gpu_layers": 99, "context_size": 2048,
            "runtime_port": 8001, "port": 8000, "verification_model": "gemini-3.5-flash-lite"}, indent=2) + "\n", encoding="utf-8")
    print(f"Ready. Start with: python scripts/run_desktop.py", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=TAG)
    install(parser.parse_args().tag)
