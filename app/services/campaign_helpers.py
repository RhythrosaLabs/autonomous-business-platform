import requests
import json
from io import BytesIO
# Optional import; handle absence gracefully
try:
    import pandas as pd  # noqa: F401
    _PANDAS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PANDAS_AVAILABLE = False

# --- Campaign Planning and Content Generation ---

def generate_content(action, prompt, budget, platforms, api_key=None):
    """Generate platform-tailored captions using Replicate API.

    Note: api_key parameter is deprecated and ignored - all generation uses Replicate.
    Returns a string or JSON string.
    """
    try:
        # ALWAYS use Replicate API (never OpenAI)
        from app.services.api_service import ReplicateAPI
        import os as _os
        repl = ReplicateAPI(_os.getenv("REPLICATE_API_TOKEN", ""))
        platforms_list = platforms if isinstance(platforms, list) else [k for k, v in platforms.items() if v]
        sys = "You write short, platform-tailored social captions with hashtags as appropriate. Output JSON with key 'post'."
        user = f"Action: {action}\nPrompt: {prompt}\nBudget: {budget}\nPlatform: {platforms_list[0] if platforms_list else 'general'}\nReturn JSON with a 'post' string of <= 300 chars."
        out = repl.generate_text(user, max_tokens=300, temperature=0.7, system_prompt=sys)
        return out
    except Exception as e:
        return f"Error: {str(e)}"

def generate_social_media_schedule(campaign_concept, platforms):
    # platforms: list of platform names (e.g., ["twitter", "facebook", "instagram"])
    optimal_times = {
        "facebook": "12:00 PM",
        "twitter": "10:00 AM",
        "instagram": "3:00 PM",
        "linkedin": "11:00 AM"
    }
    days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    schedule = {}
    for platform in platforms:
        posts = []
        for day in days_of_week:
            post_content = f"Post about {campaign_concept} on {platform.capitalize()}"
            posts.append({
                "day": day,
                "time": optimal_times.get(platform, "12:00 PM"),
                "content": post_content
            })
        schedule[platform] = posts
    return schedule

def generate_document(prompt, api_key=None):
    """Generate document content using Replicate API.
    
    Note: api_key parameter is deprecated and ignored - all generation uses Replicate.
    """
    try:
        from app.services.api_service import ReplicateAPI
        import os as _os
        repl = ReplicateAPI(_os.getenv("REPLICATE_API_TOKEN", ""))
        sys = "You are a Personal Assistant that creates detailed, professional documents."
        out = repl.generate_text(prompt, max_tokens=1024, temperature=0.7, system_prompt=sys)
        return out
    except Exception as e:
        return f"Error generating document: {e}"

def create_master_document(campaign_plan):
    master_doc = "Marketing Campaign Master Document\n\n"
    for key, value in campaign_plan.items():
        if key == "images":
            master_doc += f"{key.capitalize()}:\n"
            for img_key in value:
                master_doc += f" - {img_key}: See attached image.\n"
        else:
            master_doc += f"{key.replace('_', ' ').capitalize()}: See attached document.\n"
    return master_doc

def compile_to_pdf(campaign_plan):
    """Compile a simple PDF from campaign plan content.

    Falls back to returning plain text bytes if fpdf2 isn't installed.
    """
    try:
        from fpdf import FPDF
        from PIL import Image
    except ImportError:
        # Graceful fallback: concatenate text parts
        combined = []
        for key, value in campaign_plan.items():
            if isinstance(value, str):
                combined.append(f"## {key}\n{value}\n")
        return "\n".join(combined).encode("utf-8")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for key, value in campaign_plan.items():
        def _add_text(text: str):
            pdf.add_page()
            pdf.multi_cell(0, 10, text)
        def _add_image_bytes(b: bytes):
            try:
                image = Image.open(BytesIO(b))
                pdf.add_page()
                # Save temp file for fpdf (fpdf expects a path)
                tmp_path = f"/tmp/_campaign_img_{hash(b)}.png"
                image.save(tmp_path)
                pdf.image(tmp_path, x=10, y=8, w=190)
            except Exception as e:
                print(f"Error adding image to PDF: {e}")
        if isinstance(value, str):
            _add_text(value)
        elif isinstance(value, bytes):
            _add_image_bytes(value)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str):
                    _add_text(sub_value)
                elif isinstance(sub_value, bytes):
                    _add_image_bytes(sub_value)
    try:
        # fpdf2 returns a bytearray for dest='S'
        out = pdf.output(dest='S')
        data = bytes(out)
    except Exception:
        # Fallback: write to a temp file and read back
        import os
        tmp_pdf = "/tmp/_campaign_plan.pdf"
        pdf.output(tmp_pdf)
        with open(tmp_pdf, 'rb') as f:
            data = f.read()
        try:
            os.remove(tmp_pdf)
        except Exception:
            pass
    return data

def enhance_content(content, filename, api_key=None):
    """Enhance content using Replicate API.
    
    Note: api_key parameter is deprecated and ignored - all generation uses Replicate.
    """
    try:
        from app.services.api_service import ReplicateAPI
        import os as _os
        repl = ReplicateAPI(_os.getenv("REPLICATE_API_TOKEN", ""))
        sys = f"Enhance the following {filename} content to be more professional and engaging."
        prompt = f"Enhance this content:\n\n{content}"
        out = repl.generate_text(prompt, max_tokens=1024, temperature=0.7, system_prompt=sys)
        return out
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_and_enhance(file_path, api_key):
    # file_path: path to a file to analyze and enhance
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return enhance_content(content, file_path, api_key)
