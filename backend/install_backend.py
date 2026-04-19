from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MIN_VERSION = (3, 9)
RECOMMENDED_VERSION = (3, 11)


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.check_call(command)


def main() -> None:
    version = sys.version_info
    if version < MIN_VERSION:
        raise SystemExit("Python 3.9 이상이 필요합니다.")

    project_root = Path(__file__).resolve().parent
    requirements = project_root / "requirements.txt"

    print(f"Python 버전: {version.major}.{version.minor}.{version.micro}")
    print(f"설치 파일: {requirements.name}")
    if (version.major, version.minor) >= (3, 13):
        print("안내: Python 3.13 환경입니다. requirements.txt에서 Python 버전에 맞는 NumPy 범위를 자동 선택합니다.")
    elif (version.major, version.minor) < RECOMMENDED_VERSION:
        print("안내: Python 3.11 또는 3.12 환경이 설치 안정성과 속도 측면에서 가장 무난합니다.")

    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([sys.executable, "-m", "pip", "install", "--prefer-binary", "-r", str(requirements)])

    print("\n설치가 완료되었습니다.")
    print("다음 단계:")
    print("1) python build_index.py --input ../sample_audit_cases.csv --out ./artifacts")
    print("2) uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
