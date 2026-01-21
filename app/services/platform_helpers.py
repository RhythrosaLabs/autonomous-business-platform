import os
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

def is_streamlit_cloud():
    """Detect if running on Streamlit Cloud (files cannot be saved)."""
    return os.getenv('STREAMLIT_SHARING_MODE') is not None or            os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or            'streamlit.app' in os.getenv('HOSTNAME', '')

def get_file_save_path(filename, subfolder='generated_images'):
    """
    Get appropriate file save path. Returns None on Streamlit Cloud.
    On local, returns path in file_library.
    """
    if is_streamlit_cloud():
        return None  # Cannot save files on Streamlit Cloud
    
    base_dir = Path("file_library")
    save_dir = base_dir / subfolder
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / filename


from .secure_config import get_api_key
import streamlit as st

from app.services.api_service import PrintifyAPI
from app.services.api_service import ReplicateAPI


__all__ = [
    "_format_variant_label",
    "_get_printify_api",
    "_printify_selection_ready",
    "_send_design_to_printify",
    "_render_printify_product_config",
    "_resolve_campaign_printify_config",
    "_build_default_printify_config",
    "_ensure_replicate_client",
    "_get_replicate_token",
    "_slugify",
    "create_campaign_directory",
    "save_campaign_metadata",
    "_extract_article_html"
]



def safe_save_file(content, filename, subfolder='generated_images', file_type='binary'):
    """
    Safely save file with Streamlit Cloud check.
    Returns (success, file_path_or_none, message)
    """
    if is_streamlit_cloud():
        return (False, None, "⚠️ Cannot save files on Streamlit Cloud. Please download immediately.")
    
    try:
        save_path = get_file_save_path(filename, subfolder)
        if save_path is None:
            return (False, None, "File saving disabled in cloud mode")
        
        mode = 'wb' if file_type == 'binary' else 'w'
        with open(save_path, mode) as f:
            f.write(content)
        
        return (True, str(save_path), f"✅ Saved to {save_path}")
    except Exception as e:
        return (False, None, f"❌ Error saving file: {str(e)}")

def _get_cached_printify_api(token: str, shop_id: str) -> Optional[PrintifyAPI]:
    """Cached Printify API client."""
    try:
        return PrintifyAPI(token)
    except Exception:
        return None


def _get_printify_api() -> Optional[PrintifyAPI]:
    token = get_api_key('PRINTIFY_API_TOKEN', 'Printify API Token') or ''
    shop_id = get_api_key('PRINTIFY_SHOP_ID', 'Printify Shop ID') or ''
    if not token or not shop_id:
        return None

    # Use cached client
    api = _get_cached_printify_api(token, shop_id)
    if api:
        st.session_state.printify_api = api
        st.session_state.printify_shop_id = shop_id
    return api


def _format_variant_label(variant: dict, options_schema: list) -> str:
    option_parts = []
    variant_options = variant.get('options', [])
    for idx, value_id in enumerate(variant_options):
        if idx >= len(options_schema):
            continue
        option_info = options_schema[idx]
        value_title = next((val.get('title') for val in option_info.get('values', []) if val.get('id') == value_id), None)
        option_name = option_info.get('name')
        if option_name and value_title:
            option_parts.append(f"{option_name}: {value_title}")

    option_text = " • ".join(option_parts)
    price_cents = variant.get('price', 0)
    price_text = f"${price_cents/100:.2f}" if price_cents else ""
    title = variant.get('title') or "Variant"
    label_parts = [title]
    if option_text:
        label_parts.append(option_text)
    if price_text:
        label_parts.append(price_text)
    return " | ".join(label_parts)


def _printify_selection_ready(config: Optional[dict]) -> bool:
    return bool(
        config
        and config.get('blueprint_id')
        and config.get('provider_id')
        and config.get('variant_ids')
    )


def _load_printify_blueprints(force_refresh: bool = False) -> list:
    cache = st.session_state.get('printify_blueprints_cache')
    if cache and not force_refresh and time.time() - cache.get('timestamp', 0) < 3600:
        return cache.get('data', [])

    api = _get_printify_api()
    if not api:
        return cache.get('data', []) if cache else []

    try:
        blueprints = api.get_blueprints()
    except Exception as exc:
        st.warning("Unable to load Printify catalog. Using last cached results if available.")
        st.error(exc)
        return cache.get('data', []) if cache else []

    st.session_state['printify_blueprints_cache'] = {
        'timestamp': time.time(),
        'data': blueprints
    }
    return blueprints


def _get_printify_providers(blueprint_id: int) -> list:
    cache = st.session_state.setdefault('printify_provider_cache', {})
    if blueprint_id in cache and time.time() - cache[blueprint_id]['timestamp'] < 3600:
        return cache[blueprint_id]['data']

    api = _get_printify_api()
    if not api:
        return cache.get(blueprint_id, {}).get('data', [])

    try:
        providers = api.get_print_providers(blueprint_id)
    except Exception as exc:
        st.warning("Unable to load print providers right now.")
        st.error(exc)
        return cache.get(blueprint_id, {}).get('data', [])

    cache[blueprint_id] = {
        'timestamp': time.time(),
        'data': providers
    }
    return providers


def _get_printify_variants(blueprint_id: int, provider_id: int) -> dict:
    cache = st.session_state.setdefault('printify_variant_cache', {})
    cache_key = f"{blueprint_id}:{provider_id}"
    if cache_key in cache and time.time() - cache[cache_key]['timestamp'] < 3600:
        return cache[cache_key]['data']

    api = _get_printify_api()
    if not api:
        return cache.get(cache_key, {}).get('data', {"variants": [], "options": []})

    try:
        variants = api.get_variants(blueprint_id, provider_id)
    except Exception as exc:
        st.warning("Unable to load product variants for this provider right now.")
        st.error(exc)
        return cache.get(cache_key, {}).get('data', {"variants": [], "options": []})

    cache[cache_key] = {
        'timestamp': time.time(),
        'data': variants
    }
    return variants


def _send_design_to_printify(image_path: str, prompt: str, config: dict, variation_label: str) -> dict:
    api = _get_printify_api()
    shop_id = st.session_state.get('printify_shop_id')
    if not api or not shop_id:
        raise RuntimeError("Connect your Printify credentials in Settings first.")

    blueprint_id = config.get('blueprint_id')
    provider_id = config.get('provider_id')
    variant_ids = config.get('variant_ids') or []
    if not blueprint_id or not provider_id or not variant_ids:
        raise RuntimeError("Select a product type, provider, and at least one variant before publishing.")

    # Intelligent pricing - if price is 0 or not set, calculate based on product type
    configured_price = config.get('price', 0)
    if configured_price <= 0:
        # Calculate smart price based on product type
        from flux_static_ads_generator import calculate_smart_price
        product_type = config.get('blueprint_title', 'product').lower()
        smart_price, _ = calculate_smart_price(product_type, is_digital=False)
        price_dollars = smart_price
    else:
        price_dollars = max(configured_price, 0)
    
    price_cents = int(round(price_dollars * 100))
    scale = float(config.get('scale', 0.85))
    placement_x = float(config.get('placement_x', 0.5))
    placement_y = float(config.get('placement_y', 0.5))
    publish_live = bool(config.get('publish_live', True))
    variant_meta = config.get('variant_meta', {})

    placeholder_variant = None
    for vid in variant_ids:
        meta = variant_meta.get(str(vid)) or variant_meta.get(vid)
        if meta and meta.get('placeholders'):
            placeholder_variant = meta
            break

    if not placeholder_variant:
        raise RuntimeError("Selected variants do not include printable areas.")

    placeholder = placeholder_variant['placeholders'][0]

    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    file_name = Path(image_path).name
    upload_id = api.upload_image(image_data, file_name)

    # Generate human-like product title and description (never mention AI)
    # Strip markdown formatting for Shopify
    def strip_markdown(text: str) -> str:
        """Remove markdown formatting"""
        import re
        if not text:
            return text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
        return text
    
    product_type = config.get('blueprint_title', 'Product')
    if config.get('custom_title'):
        product_title = strip_markdown(config.get('custom_title'))[:255]
    else:
        # Clean title - just the concept + product type
        clean_prompt = prompt.split(',')[0].strip().title()
        product_title = strip_markdown(f"{clean_prompt} {product_type}")[:255]
    
    if config.get('custom_description'):
        description = strip_markdown(config.get('custom_description'))
    else:
        # Human-sounding description (never mention AI)
        try:
            from flux_static_ads_generator import generate_human_description
            desc_parts = generate_human_description(
                product_name=product_title,
                product_type=product_type,
                concept=prompt.split(',')[0].strip(),
                brand_voice="chill"
            )
            description = strip_markdown(desc_parts.get('short_description', f"Unique {product_type.lower()} featuring our {prompt.split(',')[0].strip().lower()} design."))
        except:
            description = strip_markdown(f"Unique {product_type.lower()} featuring our {prompt.split(',')[0].strip().lower()} design. Made with care.")
    
    tag_values = config.get('tags') or []

    product_payload = {
        "title": product_title,
        "description": description,
        "blueprint_id": blueprint_id,
        "print_provider_id": provider_id,
        "variants": [{
            "id": vid,
            "price": price_cents,
            "is_enabled": True
        } for vid in variant_ids],
        "print_areas": [{
            "variant_ids": variant_ids,
            "placeholders": [{
                "position": placeholder.get('position', 'front'),
                "images": [{
                    "id": upload_id,
                    "x": placement_x,
                    "y": placement_y,
                    "scale": scale,
                    "angle": 0
                }]
            }]
        }],
        "tags": tag_values
    }

    product_result = api.create_product(shop_id, product_payload)
    product_id = str(product_result.get('id')) if product_result.get('id') else None

    publish_result = None
    if publish_live and product_id:
        publish_result = api.publish_product(shop_id, product_id)

    timestamp = datetime.now().isoformat(timespec="seconds")
    record = {
        "product_id": product_id,
        "upload_id": upload_id,
        "payload": product_payload,
        "published": bool(publish_live and publish_result),
        "title": product_title,
        "blueprint_id": blueprint_id,
        "provider_id": provider_id,
        "variant_ids": variant_ids,
        "timestamp": timestamp,
        "design_path": image_path
    }

    st.session_state.setdefault('printify_products', []).append(record)
    st.session_state.setdefault('printify_uploads', []).append({
        'upload_id': upload_id,
        'design_path': image_path,
        'prompt': prompt,
        'timestamp': timestamp
    })

    return record


def _ensure_printify_config_defaults(config_key: str) -> Dict[str, Any]:
    defaults = {
        "search_query": "poster",  # Default to poster products
        "blueprint_id": None,
        "blueprint_title": None,
        "provider_id": None,
        "provider_name": None,
        "variant_ids": [],
        "variant_meta": {},
        "price": 0.0,  # 0 means auto-calculate intelligent pricing
        "scale": 0.85,
        "publish_live": True,
        "auto_send": False,
        "placement_x": 0.5,
        "placement_y": 0.5,
        "tags": [],
        "custom_title": "",
        "custom_description": ""
    }
    config: Dict[str, Any] = st.session_state.setdefault(config_key, {})
    for key, value in defaults.items():
        config.setdefault(key, value if not isinstance(value, list) else list(value))
    return config


def _render_printify_product_config(section_title: str,
                                    config_key: str = "product_studio_printify_config",
                                    allow_auto_toggle: bool = True,
                                    instructions: Optional[str] = None) -> Tuple[Dict[str, Any], bool, Any]:
    config = _ensure_printify_config_defaults(config_key)
    widget_prefix = re.sub(r'\W+', '_', config_key.lower())
    printify_api_client = _get_printify_api()

    st.markdown(f"#### 🛍️ {section_title}")
    if instructions:
        st.caption(instructions)

    if not printify_api_client:
        st.info("Connect your Printify credentials in Settings to use these controls.")
        return config, False, None

    search_query = st.text_input(
        "Search Printify catalog",
        value=config.get('search_query', ''),
        placeholder="hoodie, mug, tote bag, canvas",
        key=f"{widget_prefix}_blueprint_search"
    ) or ""

    blueprint_catalog = _load_printify_blueprints()
    filtered_catalog = []
    query_text = search_query.lower().strip()
    for blueprint in blueprint_catalog:
        category = blueprint.get('category')
        if isinstance(category, dict):
            category = category.get('title', '')
        searchable = f"{blueprint.get('title', '')} {blueprint.get('brand', '')} {category}".lower()
        if not query_text or query_text in searchable:
            filtered_catalog.append(blueprint)

    selected_blueprint = None
    blueprint_lookup = {}
    blueprint_labels = []
    if filtered_catalog:
        for blueprint in filtered_catalog:
            category = blueprint.get('category')
            if isinstance(category, dict):
                category = category.get('title', '')
            brand = blueprint.get('brand') or blueprint.get('brand_name') or ''
            descriptor = " · ".join(filter(None, [brand, category]))
            label = f"{blueprint.get('title', 'Blueprint')} (#{blueprint.get('id')})"
            if descriptor:
                label = f"{blueprint.get('title', 'Blueprint')} — {descriptor} (#{blueprint.get('id')})"
            blueprint_labels.append(label)
            blueprint_lookup[label] = blueprint

        default_label = next(
            (lbl for lbl, data in blueprint_lookup.items() if data.get('id') == config.get('blueprint_id')),
            blueprint_labels[0]
        ) if blueprint_labels else None

        blueprint_label = st.selectbox(
            "Product Type",
            blueprint_labels,
            index=blueprint_labels.index(default_label) if default_label in blueprint_labels else 0,
            key=f"{widget_prefix}_blueprint_select"
        ) if blueprint_labels else None
        selected_blueprint = blueprint_lookup.get(blueprint_label) if blueprint_label else None
    else:
        st.warning("No products match that search. Try a different keyword or clear the search box.")

    selected_provider = None
    provider_lookup = {}
    provider_labels = []
    if selected_blueprint:
        providers = _get_printify_providers(selected_blueprint.get('id'))
        if providers:
            for provider in providers:
                region = provider.get('location')
                if isinstance(region, dict):
                    region = region.get('country') or region.get('state')
                region = region or provider.get('country') or provider.get('region') or ''
                provider_label = f"{provider.get('title') or provider.get('name', 'Provider')} (#{provider.get('id')})"
                if region:
                    provider_label = f"{provider.get('title') or provider.get('name', 'Provider')} — {region} (#{provider.get('id')})"
                provider_labels.append(provider_label)
                provider_lookup[provider_label] = provider

            default_provider_label = next(
                (lbl for lbl, data in provider_lookup.items() if data.get('id') == config.get('provider_id')),
                provider_labels[0]
            ) if provider_labels else None

            provider_label = st.selectbox(
                "Print Provider",
                provider_labels,
                index=provider_labels.index(default_provider_label) if default_provider_label in provider_labels else 0,
                key=f"{widget_prefix}_provider_select"
            ) if provider_labels else None
            selected_provider = provider_lookup.get(provider_label) if provider_label else None
        else:
            st.warning("No print providers found for this product yet. Try another blueprint.")

    variant_response = {"variants": [], "options": []}
    selected_variant_ids = []
    variant_meta = {}
    if selected_blueprint and selected_provider:
        variant_response = _get_printify_variants(selected_blueprint.get('id'), selected_provider.get('id'))
        variant_list = variant_response.get('variants', [])
        options_schema = variant_response.get('options', [])
        variant_lookup = {}
        variant_labels = []
        for variant in variant_list:
            variant_id = variant.get('id')
            if variant_id is None:
                continue
            label = _format_variant_label(variant, options_schema)
            label = f"{label} (#{variant_id})"
            variant_labels.append(label)
            variant_lookup[label] = variant

        prev_ids = config.get('variant_ids') or []
        default_variant_labels = [
            label for label, data in variant_lookup.items() if data.get('id') in prev_ids
        ]
        if not default_variant_labels:
            default_variant_labels = variant_labels[:min(3, len(variant_labels))]

        if variant_labels:
            selected_variant_labels = st.multiselect(
                "Variants / Sizes / Colors",
                variant_labels,
                default=default_variant_labels,
                help="Each selected variant becomes an enabled SKU on Printify.",
                key=f"{widget_prefix}_variant_multiselect"
            )
            selected_variants = [variant_lookup[label] for label in selected_variant_labels if label in variant_lookup]
            selected_variant_ids = [variant.get('id') for variant in selected_variants if variant.get('id') is not None]
            variant_meta = {str(variant.get('id')): variant for variant in selected_variants if variant.get('id') is not None}
        else:
            st.warning("No variants available for this provider yet.")

    # Smart pricing - show suggested price based on product type
    current_price = float(config.get('price', 0.0))
    if selected_blueprint and current_price <= 0:
        try:
            from flux_static_ads_generator import calculate_smart_price
            product_type = selected_blueprint.get('title', 'product').lower()
            suggested_price, price_rationale = calculate_smart_price(product_type, is_digital=False)
            st.caption(f"💡 Suggested price for {product_type}: ${suggested_price:.2f}")
            default_price = suggested_price
        except:
            default_price = 25.0
    else:
        default_price = current_price if current_price > 0 else 25.0
    
    price_input = st.number_input(
        "Retail Price (USD) - Set to 0 for auto-pricing",
        min_value=0.0,
        max_value=150.0,
        value=default_price,
        step=1.0,
        help="Set to 0 to use intelligent auto-pricing based on product type",
        key=f"{widget_prefix}_price"
    )
    scale_pct = st.slider(
        "Design Scale (%)",
        min_value=40,
        max_value=100,
        value=int(config.get('scale', 0.85) * 100),
        key=f"{widget_prefix}_scale"
    )

    publish_live = st.checkbox(
        "Publish product immediately on Printify/Shopify",
        value=config.get('publish_live', True),
        help="When enabled, newly created products are published live in your connected store.",
        key=f"{widget_prefix}_publish_live"
    )

    auto_send = config.get('auto_send', False)
    if allow_auto_toggle:
        auto_send = st.checkbox(
            "Auto-publish each new design to Printify",
            value=config.get('auto_send', False),
            help="Automatically upload, create, and publish a Printify product for every generated design in this section.",
            key=f"{widget_prefix}_auto_send"
        )
    else:
        auto_send = False

    config.update({
        "search_query": search_query,
        "blueprint_id": selected_blueprint.get('id') if selected_blueprint else None,
        "blueprint_title": selected_blueprint.get('title') if selected_blueprint else None,
        "provider_id": selected_provider.get('id') if selected_provider else None,
        "provider_name": (selected_provider.get('title') or selected_provider.get('name')) if selected_provider else None,
        "variant_ids": selected_variant_ids,
        "variant_meta": variant_meta,
        "price": price_input,
        "scale": scale_pct / 100,
        "publish_live": publish_live,
        "auto_send": auto_send,
    })

    if _printify_selection_ready(config):
        st.caption(f"✅ Ready to publish {len(config['variant_ids'])} variant(s) of {config.get('blueprint_title', 'product')}")
    else:
        st.caption("Select a product type, provider, and at least one variant to enable Printify publishing.")

    return config, _printify_selection_ready(config), printify_api_client


def _resolve_campaign_printify_config() -> Optional[Dict[str, Any]]:
    candidates = [
        st.session_state.get('campaign_printify_config'),
        st.session_state.get('product_studio_printify_config')
    ]
    for config in candidates:
        if isinstance(config, dict) and _printify_selection_ready(config):
            return config
    return None


def _build_default_printify_config(product_type: str = "poster") -> Optional[Dict[str, Any]]:
    api = _get_printify_api()
    if not api:
        return None
    try:
        blueprint_id = api.find_blueprint(product_type)
        provider_id, variant_id, variant_info = api.get_provider_and_variant(blueprint_id)
        return {
            "blueprint_id": blueprint_id,
            "blueprint_title": product_type.title(),
            "provider_id": provider_id,
            "provider_name": None,
            "variant_ids": [variant_id],
            "variant_meta": {str(variant_id): variant_info},
            "price": 25.0,
            "scale": 0.85,
            "publish_live": True,
            "auto_send": False,
            "placement_x": 0.5,
            "placement_y": 0.5,
            "tags": [],
            "custom_title": "",
            "custom_description": ""
        }
    except Exception:
        return None


def _slugify(value: Optional[str], max_length: int = 80) -> str:
    base = (value or "item").lower().strip()
    base = re.sub(r'[^a-z0-9]+', '-', base)
    base = base.strip('-') or 'item'
    if len(base) > max_length:
        base = base[:max_length].rstrip('-')
    return base or 'item'


def _get_replicate_token() -> str:
    token = get_api_key('REPLICATE_API_TOKEN', 'Replicate API Token')
    if not token:
        raise ValueError("Add your REPLICATE_API_TOKEN in the Settings panel to enable AI generation.")
    return token


def _get_cached_replicate_client(token: str, model_name: str):
    """Cached Replicate API client."""
    return ReplicateAPI(token, model_name)


def _ensure_replicate_client(model: Optional[str] = None):
    token = _get_replicate_token()
    model_name = model or st.session_state.get('replicate_image_model', 'prunaai/flux-fast')
    # Use cached client
    replicate_client = _get_cached_replicate_client(token, model_name)
    return replicate_client, None


def create_campaign_directory(concept: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(concept or "campaign")
    base_dir = Path("campaigns") / f"{timestamp}_{slug}"
    base_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("products", "social_media", "videos", "blog_posts", "marketing_images"):
        (base_dir / sub).mkdir(parents=True, exist_ok=True)
    return base_dir


def save_campaign_metadata(campaign_dir: Path, metadata: Dict[str, Any]) -> Path:
    metadata_path = Path(campaign_dir) / "campaign_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


def _extract_article_html(html_content: str) -> str:
    lower = html_content.lower()
    start = lower.find('<article')
    end = lower.find('</article>')
    if start != -1 and end != -1:
        end = lower.find('</article>', start)
        return html_content[start:end + len('</article>')]
    return html_content
