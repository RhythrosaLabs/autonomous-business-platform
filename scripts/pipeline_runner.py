#!/usr/bin/env python3
"""
CLI bridge for the autonomous-pipeline Claude skill.
Handles Replicate (image/video/text), Printify, and Shopify operations.
All output is printed to stdout in KEY:value format for the skill to parse.

Steps:
  check            - confirm REPLICATE_API_TOKEN is set
  check-platforms  - confirm Printify + Shopify keys; print JSON status
  image            - generate image via Replicate, print IMAGE_URL or IMAGE_FILE
  video            - generate video via Replicate, print VIDEO_URL
  text             - generate text via Replicate, print to stdout
  printify         - upload image → create Printify product → publish to Shopify
  shopify-product  - create a Shopify product draft directly
  shopify-blog     - create a Shopify blog post draft
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── helpers ──────────────────────────────────────────────────────────────────

def _replicate_api():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        print("NO_API_KEY", flush=True)
        sys.exit(0)
    from app.services.api_service import ReplicateAPI
    return ReplicateAPI(token)


def _printify_api():
    token = os.environ.get("PRINTIFY_API_TOKEN", "")
    if not token:
        return None
    from app.services.api_service import PrintifyAPI
    return PrintifyAPI(token)


def _shopify_api():
    from app.services.shopify_service import ShopifyAPI
    api = ShopifyAPI()
    return api if api.connected else None


def _fetch_image_bytes(url: str) -> bytes:
    import requests
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def _blueprint_for_concept(concept: str) -> str:
    """Return Printify blueprint search term from concept keywords."""
    c = concept.lower()
    if any(k in c for k in ["hoodie", "sweatshirt", "pullover"]):
        return "Unisex Hoodie"
    if any(k in c for k in ["shirt", "tee", "tshirt", "t-shirt", "apparel", "wear"]):
        return "Unisex T-Shirt"
    if any(k in c for k in ["mug", "cup", "coffee", "tea"]):
        return "Mug"
    if any(k in c for k in ["canvas", "stretched canvas"]):
        return "Canvas"
    # Default: poster — works for any art/design concept
    return "Poster"


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_check():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    print("API_KEY_PRESENT" if token else "NO_API_KEY", flush=True)


def cmd_check_platforms():
    status = {
        "replicate": bool(os.environ.get("REPLICATE_API_TOKEN")),
        "printify":  bool(os.environ.get("PRINTIFY_API_TOKEN")),
        "shopify":   bool(
            os.environ.get("SHOPIFY_ACCESS_TOKEN") and os.environ.get("SHOPIFY_SHOP_URL")
        ),
    }
    print(f"PLATFORM_STATUS:{json.dumps(status)}", flush=True)


def cmd_image(prompt: str, width: int = 1024, height: int = 1024, output_dir: str | None = None):
    api = _replicate_api()
    url = api.generate_image(prompt=prompt, width=width, height=height, aspect_ratio="1:1")
    if output_dir and url:
        import hashlib, pathlib, requests
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
        slug = hashlib.md5(prompt.encode()).hexdigest()[:8]
        dest = pathlib.Path(output_dir) / f"image_{slug}.png"
        dest.write_bytes(requests.get(url, timeout=60).content)
        print(f"IMAGE_FILE:{dest}", flush=True)
    else:
        print(f"IMAGE_URL:{url}", flush=True)


def cmd_video(prompt: str, image_url: str, aspect_ratio: str = "16:9"):
    api = _replicate_api()
    url = api.generate_video(
        prompt=prompt, image_url=image_url, aspect_ratio=aspect_ratio, motion_level=3
    )
    print(f"VIDEO_URL:{url}", flush=True)


def cmd_text(prompt: str, max_tokens: int = 800, temperature: float = 0.7):
    api = _replicate_api()
    text = api.generate_text(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
    print(text, flush=True)


def cmd_printify(
    image_url: str,
    title: str,
    description: str,
    tags: list[str],
    concept: str,
    price_cents: int = 2499,
    publish_live: bool = True,
):
    """Upload image to Printify, create product, optionally publish to Shopify."""
    papi = _printify_api()
    if not papi:
        print("PRINTIFY_SKIPPED:no API token", flush=True)
        return

    # Get shop
    shops = papi.get_shops()
    if not shops:
        print("PRINTIFY_ERROR:no shops found", flush=True)
        return
    shop_id = str(shops[0]["id"])

    # Detect blueprint from concept
    blueprint_keyword = _blueprint_for_concept(concept)
    try:
        blueprint_id = papi.find_blueprint(blueprint_keyword)
    except Exception:
        # Fallback: poster
        blueprint_id = papi.find_blueprint("Poster")

    # Get provider + variants
    try:
        provider_id, variant_id, variant_details = papi.get_provider_and_variant(blueprint_id)
    except Exception as e:
        print(f"PRINTIFY_ERROR:could not get provider — {e}", flush=True)
        return

    # Download + upload image
    try:
        image_bytes = _fetch_image_bytes(image_url)
        upload_id = papi.upload_image(image_bytes, "pipeline_design.png")
    except Exception as e:
        print(f"PRINTIFY_ERROR:image upload failed — {e}", flush=True)
        return

    # Determine placeholder position from blueprint type
    position = "front"
    if "poster" in blueprint_keyword.lower() or "canvas" in blueprint_keyword.lower():
        position = "front"

    variant_ids = [variant_id]
    product_payload = {
        "title": title,
        "description": description,
        "blueprint_id": blueprint_id,
        "print_provider_id": provider_id,
        "variants": [{"id": vid, "price": price_cents, "is_enabled": True} for vid in variant_ids],
        "print_areas": [
            {
                "variant_ids": variant_ids,
                "placeholders": [
                    {
                        "position": position,
                        "images": [
                            {"id": upload_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}
                        ],
                    }
                ],
            }
        ],
        "tags": tags,
    }

    try:
        product_result = papi.create_product(shop_id, product_payload)
        product_id = str(product_result.get("id", ""))
    except Exception as e:
        print(f"PRINTIFY_ERROR:create product failed — {e}", flush=True)
        return

    # Publish
    if publish_live and product_id:
        try:
            papi.publish_product(shop_id, product_id)
            print(f"PRINTIFY_PRODUCT_ID:{product_id}", flush=True)
            print(f"PRINTIFY_PUBLISHED:true", flush=True)
        except Exception as e:
            print(f"PRINTIFY_PRODUCT_ID:{product_id}", flush=True)
            print(f"PRINTIFY_PUBLISH_ERROR:{e}", flush=True)
    else:
        print(f"PRINTIFY_PRODUCT_ID:{product_id}", flush=True)
        print(f"PRINTIFY_PUBLISHED:false", flush=True)


def cmd_shopify_product(title: str, description_html: str, tags: list[str], image_url: str):
    """Create a Shopify product draft."""
    sapi = _shopify_api()
    if not sapi:
        print("SHOPIFY_SKIPPED:not connected", flush=True)
        return

    try:
        product = sapi.create_product(
            title=title,
            body_html=description_html,
            vendor="",
            product_type="",
            tags=tags,
            images=[image_url] if image_url else [],
        )
        if product:
            product_id = product.get("id", "")
            shop_url = os.environ.get("SHOPIFY_SHOP_URL", "").replace("https://", "").strip("/")
            print(f"SHOPIFY_PRODUCT_ID:{product_id}", flush=True)
            print(f"SHOPIFY_PRODUCT_URL:https://{shop_url}/admin/products/{product_id}", flush=True)
        else:
            print("SHOPIFY_PRODUCT_ERROR:create returned None", flush=True)
    except Exception as e:
        print(f"SHOPIFY_PRODUCT_ERROR:{e}", flush=True)


def cmd_shopify_blog(
    title: str,
    body_html: str,
    tags: list[str],
    image_url: str,
    published: bool = False,
):
    """Create a Shopify blog post (draft by default)."""
    sapi = _shopify_api()
    if not sapi:
        print("SHOPIFY_BLOG_SKIPPED:not connected", flush=True)
        return

    try:
        article = sapi.create_blog_post(
            title=title,
            body_html=body_html,
            author="Autonomous Pipeline",
            tags=tags or [],
            published=published,
            image_url=image_url or None,
        )
        if article:
            article_id = article.get("id", "")
            article_url = article.get("url", "")
            status = "published" if published else "draft"
            print(f"SHOPIFY_BLOG_ID:{article_id}", flush=True)
            print(f"SHOPIFY_BLOG_URL:{article_url}", flush=True)
            print(f"SHOPIFY_BLOG_STATUS:{status}", flush=True)
        else:
            print("SHOPIFY_BLOG_ERROR:create returned None", flush=True)
    except Exception as e:
        print(f"SHOPIFY_BLOG_ERROR:{e}", flush=True)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step",
        required=True,
        choices=["check", "check-platforms", "image", "video", "text",
                 "printify", "shopify-product", "shopify-blog"],
    )
    # Shared
    parser.add_argument("--prompt", default="")
    parser.add_argument("--concept", default="")
    parser.add_argument("--title", default="")
    # Image
    parser.add_argument("--image-url", default="")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--output-dir", default="")
    # Video
    parser.add_argument("--aspect-ratio", default="16:9")
    # Text
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--temperature", type=float, default=0.7)
    # Printify / Shopify shared
    parser.add_argument("--description", default="")          # plain text or HTML
    parser.add_argument("--description-file", default="")     # path to file with HTML body
    parser.add_argument("--tags", default="")                 # comma-separated
    parser.add_argument("--price-cents", type=int, default=2499)
    parser.add_argument("--publish-live", action="store_true", default=False)
    # Blog
    parser.add_argument("--published", action="store_true", default=False)

    args = parser.parse_args()

    # Resolve description from file if provided
    description = args.description
    if args.description_file and os.path.exists(args.description_file):
        with open(args.description_file) as f:
            description = f.read()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    if args.step == "check":
        cmd_check()
    elif args.step == "check-platforms":
        cmd_check_platforms()
    elif args.step == "image":
        cmd_image(args.prompt, args.width, args.height, args.output_dir or None)
    elif args.step == "video":
        cmd_video(args.prompt, args.image_url, args.aspect_ratio)
    elif args.step == "text":
        cmd_text(args.prompt, args.max_tokens, args.temperature)
    elif args.step == "printify":
        cmd_printify(
            image_url=args.image_url,
            title=args.title or args.concept[:80],
            description=description,
            tags=tags,
            concept=args.concept or args.title,
            price_cents=args.price_cents,
            publish_live=args.publish_live,
        )
    elif args.step == "shopify-product":
        cmd_shopify_product(
            title=args.title,
            description_html=description,
            tags=tags,
            image_url=args.image_url,
        )
    elif args.step == "shopify-blog":
        cmd_shopify_blog(
            title=args.title,
            body_html=description,
            tags=tags,
            image_url=args.image_url,
            published=args.published,
        )


if __name__ == "__main__":
    main()
