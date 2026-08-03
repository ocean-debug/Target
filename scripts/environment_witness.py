from __future__ import annotations

import platform
import subprocess
import sys


def main() -> None:
    try:
        import torch

        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "unavailable"
    except ImportError:
        try:
            gpu = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                text=True,
            ).splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            gpu = "unavailable"
    print(f"REMOTE_HOST={platform.node()}")
    print(f"PYTHON_VERSION={sys.version.split()[0]}")
    print(f"GPU0={gpu}")
    print("V2_VALIDATION=OK")


if __name__ == "__main__":
    main()
