#!/usr/bin/env python3
"""
CLI bridge for the autonomous-pipeline Claude skill.
Invokes the existing ReplicateAPI for image/video/text generation
and prints the result URL or text to stdout.

Usage (called by the Claude skill via Bash):
  python scripts/pipeline_runner.py --step image --prompt "..." [--output-dir PATH]
  python scripts/pipeline_runner.py --step video --prompt "..." --image-url URL
  python scripts/pipeline_runner.py --step text  --prompt "..." [--max-tokens 800]
  python scripts/pipeline_runner.py --step check  # just confirms API key is present
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_api():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        print("NO_API_KEY", flush=True)
        sys.exit(0)
    from app.services.api_service import ReplicateAPI
    return ReplicateAPI(token)


def cmd_check():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    print("API_KEY_PRESENT" if token else "NO_API_KEY", flush=True)


def cmd_image(prompt: str, width: int = 1024, height: int = 1024, output_dir: str | None = None):
    api = get_api()
    url = api.generate_image(prompt=prompt, width=width, height=height, aspect_ratio="1:1")
    if output_dir and url:
        import requests, hashlib, pathlib
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
        slug = hashlib.md5(prompt.encode()).hexdigest()[:8]
        dest = pathlib.Path(output_dir) / f"image_{slug}.png"
        r = requests.get(url, timeout=60)
        dest.write_bytes(r.content)
        print(f"IMAGE_FILE:{dest}", flush=True)
    else:
        print(f"IMAGE_URL:{url}", flush=True)


def cmd_video(prompt: str, image_url: str, aspect_ratio: str = "16:9"):
    api = get_api()
    url = api.generate_video(prompt=prompt, image_url=image_url, aspect_ratio=aspect_ratio, motion_level=3)
    print(f"VIDEO_URL:{url}", flush=True)


def cmd_text(prompt: str, max_tokens: int = 800, temperature: float = 0.7):
    api = get_api()
    text = api.generate_text(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
    print(text, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True, choices=["check", "image", "video", "text"])
    parser.add_argument("--prompt", default="")
    parser.add_argument("--image-url", default="")
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    if args.step == "check":
        cmd_check()
    elif args.step == "image":
        cmd_image(args.prompt, args.width, args.height, args.output_dir or None)
    elif args.step == "video":
        cmd_video(args.prompt, args.image_url, args.aspect_ratio)
    elif args.step == "text":
        cmd_text(args.prompt, args.max_tokens, args.temperature)


if __name__ == "__main__":
    main()
