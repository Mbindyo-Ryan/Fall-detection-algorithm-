#!/usr/bin/env python3
"""
Create a single ZIP bundle that mirrors the reviewer-friendly package style
shown in OmondiKevin/toxicity-detector.
"""

import argparse
import os
from pathlib import Path
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INCLUDE_FILES = [
    "README.md",
    "RUN_INSTRUCTIONS.md",
    "REVIEWER_GUIDE.md",
    "PROJECT_DOCUMENTATION.md",
    "VIDEO_TESTING_GUIDE.md",
    "CNN_INTEGRATION_GUIDE.md",
    "QUICK_VIDEO_TEST.md",
    "PROJECT_ROADMAP.md",
    "PROJECT_WALKTHROUGH.md",
    "Makefile",
    "requirements.txt",
    "app_auth.py",
    "detection_skeleton.py",
    "alert_service.py",
    "test_results.json",
]

INCLUDE_DIRS = [
    "templates",
    "scripts",
    "models",
    "fall_videos",
    "data",
]


def add_path(zip_file: zipfile.ZipFile, path: Path):
    if path.is_file():
        zip_file.write(path, arcname=path.relative_to(PROJECT_ROOT))
    elif path.is_dir():
        for root, _, files in os.walk(path):
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(PROJECT_ROOT)
                zip_file.write(full_path, arcname=arcname)


def build_bundle(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel_file in INCLUDE_FILES:
            file_path = PROJECT_ROOT / rel_file
            if file_path.exists():
                add_path(archive, file_path)
        for rel_dir in INCLUDE_DIRS:
            dir_path = PROJECT_ROOT / rel_dir
            if dir_path.exists():
                add_path(archive, dir_path)
    print(f"✅ Release package created at {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Package fall detection release bundle.")
    parser.add_argument(
        "--output",
        default=PROJECT_ROOT / "dist" / "care-system-release.zip",
        type=Path,
        help="Path to the output ZIP archive.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_bundle(args.output)

