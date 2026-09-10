"""Explicit one-time model download. The application itself never uses the network."""
import hashlib
from pathlib import Path
import urllib.request

URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
DESTINATION = Path(__file__).resolve().parents[1] / 'models' / 'hand_landmarker.task'


def main():
    DESTINATION.parent.mkdir(exist_ok=True)
    checksum_file = DESTINATION.with_suffix('.sha256')
    expected = checksum_file.read_text().split()[0] if checksum_file.exists() else None
    if DESTINATION.exists() and expected and hashlib.sha256(DESTINATION.read_bytes()).hexdigest() == expected:
        print('Verified local model:', DESTINATION)
        return
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000 or len(data) < 1_000_000:
        raise RuntimeError('Unexpected model size; download rejected')
    digest = hashlib.sha256(data).hexdigest()
    if expected and digest != expected:
        raise RuntimeError('Model checksum mismatch; download rejected')
    temporary = DESTINATION.with_suffix('.tmp')
    temporary.write_bytes(data)
    temporary.replace(DESTINATION)
    print('Downloaded model:', DESTINATION, '\nSHA256:', digest)


if __name__ == '__main__':
    main()
