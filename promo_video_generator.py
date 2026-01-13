"""
promo_video_generator.py

Product-specific AI promo video generator for the pipeline.
- Generates a 4-segment promo script for a product.
- Optionally generates images for each segment.
- Optionally assembles a simple video (using images and text overlays).
- Exports script and assets.

Dependencies:
- Replicate (for text and image generation)
- requests (for image generation API)
- moviepy (optional, for video assembly)
"""

import os as os_module
import requests
from datetime import datetime
from api_service import ReplicateAPI

# Optional: import moviepy for video assembly
try:
    import moviepy.editor as mpy
    MOVIEPY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    mpy = None
    MOVIEPY_AVAILABLE = False

# Use Replicate API for promo script generation
def generate_promo_script(product_name, target_audience, ad_tone, key_benefits, call_to_action, replicate_token=None):
    """
    Generate a 4-segment promo script for the product using Replicate GPT-OSS-20B.
    """
    if not replicate_token:
        import os
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    if not replicate_token or not replicate_token.strip():
        raise ValueError("Replicate API token is missing. Please provide a valid token before running the workflow.")

    prompt = f"""
    You are an expert advertising copywriter. Write a compelling, persuasive 20-second video ad script for '{product_name}'.

    Target Audience: {target_audience}
    Tone: {ad_tone}
    Key Benefits: {key_benefits}
    Call to Action: {call_to_action}

    Create a 4-segment script (5 seconds each) that follows this structure:
    1: Hook/Problem - Grab attention with a relatable problem or exciting opening
    2: Solution - Introduce the product as the perfect solution
    3: Benefits - Highlight the key benefits that matter to the target audience
    4: Call to Action - Strong, compelling call to action with urgency

    Keep each segment to 6-8 words maximum for clear delivery. Make it persuasive and memorable.
    Label each section as '1:', '2:', '3:', and '4:'.
    """

    replicate_api = ReplicateAPI(replicate_token)
    content = replicate_api.generate_text(prompt, max_tokens=400, temperature=0.9)

    if not content or not content.strip():
        raise RuntimeError("No output from Replicate text model. Please check your model, prompt, and API token.")

    # Extract segments
    import re
    segments = re.findall(r"\d+:\s*(.+)", content)
    if len(segments) < 4:
        raise ValueError("Failed to extract 4 clear script segments from Replicate output. Output was:\n" + str(content))
    return segments

def generate_image(prompt, output_path, replicate_token=None):
    """
    Generate an image using Replicate Flux Fast endpoint.
    """
    if not replicate_token:
        import os
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    replicate_api = ReplicateAPI(replicate_token)
    image_url = replicate_api.generate_image(prompt, width=1024, height=1024)
    img_data = requests.get(image_url).content
    with open(output_path, "wb") as f:
        f.write(img_data)
    return output_path

def export_script(segments, product_name, output_dir):
    """
    Save the promo script to a text file.
    """
    os_module.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_path = os_module.path.join(output_dir, f"{product_name}_promo_script_{timestamp}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"Segment {i+1}: {seg}\n")
    return script_path

def generate_video_from_image(image_path, output_path, replicate_token=None):
    """
    Generate a ~10s promo video from a single image using Replicate Kling 2.5 Turbo Pro.
    """
    if not replicate_token:
        import os
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    replicate_api = ReplicateAPI(replicate_token)
    # Upload image to a public URL if needed (Replicate may require a URL, not a local file)
    # For now, assume image_path is a local file and user has a way to serve it or upload to a temp host
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    # Convert local image to data URI for Replicate API
    import base64
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Determine mime type
    ext = os_module.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    if ext == ".webp": mime_type = "image/webp"
    
    image_url = f"data:{mime_type};base64,{encoded_string}"
    # Use the filename as a simple prompt seed
    basename = os_module.path.basename(image_path)
    video_url = replicate_api.generate_video(prompt=f"Promo for {basename}", image_url=image_url, aspect_ratio="16:9", motion_level=4)
    video_data = requests.get(video_url).content
    with open(output_path, "wb") as f:
        f.write(video_data)
    return output_path

def generate_voiceover(text, output_path, replicate_token=None, model="minimax/speech-02-hd", voice="alloy", output_format="mp3"):
    """
    Generate a voiceover audio file from text using Replicate TTS API.
    """
    if not replicate_token:
        import os
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    replicate_api = ReplicateAPI(replicate_token)
    audio_url = replicate_api.generate_speech(text, voice=voice, format=output_format)
    audio_data = requests.get(audio_url).content
    with open(output_path, "wb") as f:
        f.write(audio_data)
    return output_path

def assemble_video_from_images(image_paths, segments, product_name, output_dir, duration_per_segment=5):
    """
    Optionally assemble a simple video from images and text overlays.
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError("moviepy is not installed. Install it to enable video assembly.")
    # Import locally to avoid unbound names when optional dependency is missing
    from moviepy.editor import ImageClip, concatenate_videoclips, TextClip, CompositeVideoClip
    clips = []
    for img_path, text in zip(image_paths, segments):
        img_clip = ImageClip(img_path).set_duration(duration_per_segment)
        txt_clip = TextClip(text, fontsize=36, color='white', bg_color='rgba(0,0,0,0.5)', size=img_clip.size).set_duration(duration_per_segment).set_position('center')
        composite = CompositeVideoClip([img_clip, txt_clip])
        clips.append(composite)
    final_video = concatenate_videoclips(clips, method="compose")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os_module.path.join(output_dir, f"{product_name}_promo_{timestamp}.mp4")
    final_video.write_videofile(video_path, fps=24, codec="libx264", audio=False)
    return video_path

def generate_product_promo(product_name, target_audience, ad_tone, key_benefits, call_to_action, run_folder, make_video=False, image_path=None, replicate_token=None):
    """
    Main function to generate promo script (and optionally video) for a product.
    All outputs are saved in run_folder.
    """
    os_module.makedirs(run_folder, exist_ok=True)
    segments = generate_promo_script(product_name, target_audience, ad_tone, key_benefits, call_to_action, replicate_token=replicate_token)
    if image_path:
        image_paths = [image_path] * len(segments)
    else:
        image_paths = []
        for i, seg in enumerate(segments):
            img_path = os_module.path.join(run_folder, f"{product_name}_promo_img_{i+1}.jpg")
            generate_image(f"{product_name} promo {seg}", img_path, replicate_token=replicate_token)
            image_paths.append(img_path)
    script_path = export_script(segments, product_name, run_folder)
    video_path = None
    if make_video and MOVIEPY_AVAILABLE and image_paths:
        video_path = os_module.path.join(run_folder, f"{product_name}_promo_video.mp4")
        video_path = generate_video_from_image(image_paths[0], video_path, replicate_token=replicate_token)
    return script_path, image_paths, video_path

# Example usage (to be called from pipeline or UI)
if __name__ == "__main__":  # pragma: no cover - manual example
    product = "Printify Pro"
    audience = "Tech Enthusiasts"
    tone = "Exciting & Energetic"
    benefits = "Fast setup, global reach, high profit margins"
    cta = "Sign up now and start selling!"
    run_folder = os_module.path.join(os_module.getcwd(), "runs", "promo_demo")
    script_file, images, video = generate_product_promo(product, audience, tone, benefits, cta, run_folder=run_folder, make_video=False)
    print(f"Promo script: {script_file}")
    print(f"Images: {images}")
    if video:
        print(f"Promo video: {video}")
