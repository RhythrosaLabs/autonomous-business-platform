# api_service.py
import requests
import json
from datetime import datetime
from typing import Optional, Any, Iterable
import os
import time

class PrintifyAPI:
    """Encapsulated Printify API operations"""

    BASE_URL = "https://api.printify.com/v1"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {"Authorization": f"Bearer {api_token}"}

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request with error handling"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {**self.headers, **kwargs.pop('headers', {})}

        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Please check your connection.")
        except requests.exceptions.HTTPError as e:
            error_msg = f"API Error ({e.response.status_code})"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail}"
            except (ValueError, AttributeError):
                error_msg += f": {e.response.text[:200]}"
            raise Exception(error_msg)

    def get_shops(self) -> list[dict]:
        """Get all shops"""
        response = self._request('GET', 'shops.json')
        return response.json()

    def get_blueprints(self) -> list[dict]:
        """Get all available blueprints"""
        response = self._request('GET', 'catalog/blueprints.json')
        return response.json()

    def find_blueprint(self, product_type: str) -> int:
        """Find blueprint ID by product type"""
        blueprints = self.get_blueprints()
        for bp in blueprints:
            if product_type.lower() in bp.get("title", "").lower():
                return bp["id"]
        raise Exception(f"No blueprint found for '{product_type}'")

    def get_print_providers(self, blueprint_id: int) -> list[dict]:
        """Get print providers for blueprint"""
        response = self._request('GET', f'catalog/blueprints/{blueprint_id}/print_providers.json')
        return response.json()

    def get_variants(self, blueprint_id: int, provider_id: int) -> dict:
        """Get variants for provider"""
        response = self._request('GET',
                                 f'catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json')
        return response.json()

    def get_provider_and_variant(self, blueprint_id: int):
        """Find first available provider and variant for a blueprint"""
        providers = self.get_print_providers(blueprint_id)
        for provider in providers:
            provider_id = provider["id"]
            variants_resp = self.get_variants(blueprint_id, provider_id)
            variants_list = variants_resp.get("variants", [])
            if variants_list:
                return provider_id, variants_list[0]["id"], variants_list[0]
        raise Exception("No provider or variant found for the selected blueprint")

    def create_product(self, shop_id: str, product_data: dict) -> dict:
        """Create product in shop"""
        response = self._request('POST', f'shops/{shop_id}/products.json',
                                 headers={"Content-Type": "application/json"},
                                 json=product_data)
        return response.json()

    def publish_product(self, shop_id: str, product_id: str) -> dict:
        """Publish product to make it live"""
        response = self._request('POST', f'shops/{shop_id}/products/{product_id}/publish.json',
                                 headers={"Content-Type": "application/json"},
                                 json={"title": True, "description": True, "images": True, "variants": True, "tags": True})
        return response.json()

    def get_shop_products(self, shop_id: str, limit: int = 50, page: int = 1) -> list[dict]:
        """Get all products from a shop (max limit: 50 per Printify API)"""
        response = self._request('GET', f'shops/{shop_id}/products.json', 
                                params={'limit': min(limit, 50), 'page': page})
        return response.json().get('data', [])

    def get_product_mockup(self, shop_id: str, product_id: str) -> str:
        """Get mockup image URL for a published product (returns first/main mockup)"""
        try:
            response = self._request('GET', f'shops/{shop_id}/products/{product_id}.json')
            product_data = response.json()
            
            # Get first image from product images array
            images = product_data.get('images', [])
            if images and len(images) > 0:
                # Return the first mockup image URL
                return images[0].get('src', '')
            
            return None
        except Exception as e:
            print(f"Failed to get mockup: {e}")
            return None

    def get_all_product_mockups(self, shop_id: str, product_id: str) -> list:
        """Get ALL mockup image URLs for a published product (including lifestyle mockups)"""
        try:
            response = self._request('GET', f'shops/{shop_id}/products/{product_id}.json')
            product_data = response.json()
            
            # Get ALL images from product images array
            images = product_data.get('images', [])
            mockup_urls = []
            
            for img in images:
                src = img.get('src', '')
                if src:
                    mockup_urls.append({
                        'url': src,
                        'is_default': img.get('is_default', False),
                        'position': img.get('position', 0)
                    })
            
            # Sort by position to get lifestyle/environment mockups (usually after default)
            mockup_urls.sort(key=lambda x: x['position'])
            
            return mockup_urls
        except Exception as e:
            print(f"Failed to get all mockups: {e}")
            return []

    def upload_image(self, image_data: bytes, file_name: str) -> str:
        """Upload image to Printify"""
        import base64
        encoded = base64.b64encode(image_data).decode("utf-8")
        payload = {"file_name": file_name, "contents": encoded}
        response = self._request('POST', 'uploads/images.json',
                                 headers={"Content-Type": "application/json"},
                                 json=payload)
        return response.json()["id"]


class ReplicateAPI:
    """Unified Replicate API client wrapping the official Replicate Python SDK.

    Supported model families (aligned with user requirements):
      - Image generation (main product design, social assets): prunaai/flux-fast
      - Text generation (descriptions, hashtags, scripts): openai/gpt-oss-120b
      - Video generation (prompt or image to video): kwaivgi/kling-v2.5-turbo-pro
      - Speech synthesis (narration / voiceover): minimax/speech-02-hd

    Local mode (image only) still supported via LocalModelsManager when use_local=True.
    """

    # Latest working models - updated Dec 2025
    DEFAULT_IMAGE_MODEL = "prunaai/flux-fast"  # Fast Flux model
    DEFAULT_TEXT_MODEL = "meta/meta-llama-3-70b-instruct"  # Llama 3 70B - fast and reliable
    FAST_TEXT_MODEL = "meta/meta-llama-3-8b-instruct"  # Fast Llama 3 8B for speed mode
    PREMIUM_TEXT_MODEL = "anthropic/claude-4.5-sonnet"  # Claude 4.5 Sonnet (slower but premium)
    DEFAULT_VIDEO_MODEL = "kwaivgi/kling-v2.5-turbo-pro"  # Kling v2.5 turbo pro
    DEFAULT_SPEECH_MODEL = "minimax/speech-02-hd"  # Speech synthesis HD
    
    # ControlNet models for guided generation (Nov 2025)
    DEFAULT_MULTI_CONTROLNET_MODEL = "usamaehsan/flux-multi-controlnet"  # Multiple control inputs
    DEFAULT_STYLE_CONTROLNET_MODEL = "camenduru/visual-style-prompting-controlnet"  # Brand consistency
    DEFAULT_CANNY_MODEL = "jagilley/controlnet-canny"  # Edge detection control
    DEFAULT_DEPTH_MODEL = "cjwbw/midas"  # Depth map generation
    
    BASE_URL = "https://api.replicate.com/v1"

    def __init__(self, api_token: str, flux_model: Optional[str] = None,
                 local_manager: Any = None, use_local: bool = False):
        """Initialize Replicate client.

        Args:
            api_token: Replicate API token.
            flux_model: Optional override for image model (defaults to flux-fast).
            local_manager: LocalModelsManager for offline generation.
            use_local: If True and local_manager provided, image generation will use local pipeline.
        """
        import replicate  # noqa: F401 (kept for clarity; functions used in _run_model)
        self.api_token = api_token
        if api_token:
            os.environ["REPLICATE_API_TOKEN"] = api_token  # replicate uses env var
        self.image_model = flux_model or self.DEFAULT_IMAGE_MODEL
        self.text_model = self.DEFAULT_TEXT_MODEL
        self.video_model = self.DEFAULT_VIDEO_MODEL
        self.speech_model = self.DEFAULT_SPEECH_MODEL
        self.local_manager = local_manager
        self.use_local = use_local
        # Cache resolved model refs (owner/name -> owner/name:version-id)
        self._version_cache = {}
        self._http_session = requests.Session()

    def _prepare_file_input(self, file_obj):
        """
        Convert Streamlit UploadedFile or file-like object to data URI for Replicate
        
        Args:
            file_obj: File object (UploadedFile, BytesIO, etc.)
            
        Returns:
            str: Data URI string (data:mime/type;base64,...)
        """
        import base64
        from io import BytesIO
        
        # Handle Streamlit UploadedFile
        if hasattr(file_obj, 'read') and hasattr(file_obj, 'name'):
            # Get file content
            content = file_obj.read()
            # Reset pointer if possible
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            # Determine MIME type from file extension
            file_name = getattr(file_obj, 'name', '')
            if file_name.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif file_name.lower().endswith('.png'):
                mime_type = 'image/png'
            elif file_name.lower().endswith('.webp'):
                mime_type = 'image/webp'
            elif file_name.lower().endswith('.gif'):
                mime_type = 'image/gif'
            elif file_name.lower().endswith(('.mp4', '.mov')):
                mime_type = 'video/mp4'
            elif file_name.lower().endswith('.webm'):
                mime_type = 'video/webm'
            elif file_name.lower().endswith('.mp3'):
                mime_type = 'audio/mpeg'
            elif file_name.lower().endswith('.wav'):
                mime_type = 'audio/wav'
            else:
                mime_type = 'application/octet-stream'
            
            # Create data URI
            encoded = base64.b64encode(content).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
        
        # If already a string (URL or data URI), return as-is
        if isinstance(file_obj, str):
            return file_obj
        
        # Fallback
        return str(file_obj)

    def _run_model(self, model_ref: str, input_data: dict, max_retries: int = 3):
        """
        Run a model using the official Replicate client with retry logic for rate limiting.
        
        Args:
            model_ref: Model reference (e.g., "black-forest-labs/flux-schnell")
            input_data: Model input parameters
            max_retries: Maximum number of retry attempts for rate limiting
            
        Returns:
            Model output
        """
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }

        retry_count = 0
        base_delay = 12  # Start with 12 seconds (rate limit is 6/minute = 10s between requests)
        
        while retry_count <= max_retries:
            try:
                # Prepare input data - convert any file uploads to data URIs
                prepared_input = {}
                for key, value in input_data.items():
                    # Check if value looks like a file object
                    if hasattr(value, 'read') or (hasattr(value, '__class__') and 'UploadedFile' in str(value.__class__)):
                        prepared_input[key] = self._prepare_file_input(value)
                    else:
                        prepared_input[key] = value
                
                version_id = self._resolve_model_version(model_ref)
                payload = {"version": version_id, "input": prepared_input}

                response = self._http_session.post(
                    f"{self.BASE_URL}/predictions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                # Handle rate limiting with retry
                if response.status_code == 429 or "throttled" in response.text.lower():
                    if retry_count < max_retries:
                        retry_count += 1
                        delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff: 12s, 24s, 48s
                        import logging
                        logging.warning(f"Rate limit hit. Retrying in {delay}s (attempt {retry_count}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} retries: {response.text[:200]}")
                
                if response.status_code not in (200, 201):
                    raise Exception(f"Initial request failed: {response.text[:200]}")

                data = response.json()
                status_url = data.get("urls", {}).get("get")

                # Poll until prediction completes (with timeout)
                # Video editing can take much longer, so increase timeout
                max_poll_time = 900  # 15 minute timeout for video/3D operations (increased from 5 min)
                poll_start = time.time()
                while data.get("status") in {"starting", "processing"}:
                    # Check for timeout
                    if time.time() - poll_start > max_poll_time:
                        # Try to cancel the prediction
                        cancel_url = data.get("urls", {}).get("cancel")
                        if cancel_url:
                            try:
                                self._http_session.post(cancel_url, headers=headers, timeout=5)
                            except Exception:
                                pass  # Best effort cancellation
                        raise Exception(f"Prediction timed out after {max_poll_time}s. The API may be overloaded.")
                    
                    time.sleep(2)
                    if not status_url:
                        raise Exception("Prediction did not provide status URL")
                    status_resp = self._http_session.get(status_url, headers=headers, timeout=30)
                    data = status_resp.json()

                if data.get("status") != "succeeded":
                    raise Exception(f"Prediction failed: {data.get('error')}")

                return data.get("output", [])

            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error in the exception
                if "throttled" in error_str.lower() and retry_count < max_retries:
                    retry_count += 1
                    delay = base_delay * (2 ** (retry_count - 1))
                    import logging
                    logging.warning(f"Rate limit in error. Retrying in {delay}s (attempt {retry_count}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(f"Replicate API error: {error_str}")

    def _resolve_model_version(self, model_ref: str) -> str:
        """Resolve the latest version ID for a model, with caching."""
        if ":" in model_ref:
            # Caller already provided explicit version reference; strip to hash portion
            return model_ref.split(":", 1)[1]

        cached = self._version_cache.get(model_ref)
        if cached:
            return cached

        if not self.api_token:
            raise Exception("Replicate API token not set; cannot resolve model version")

        owner, name = model_ref.split("/", 1)
        url = f"{self.BASE_URL}/models/{owner}/{name}"
        headers = {"Authorization": f"Token {self.api_token}"}

        response = self._http_session.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Failed to resolve version for {model_ref}: {response.text[:200]}")

        data = response.json()
        version_info = data.get("latest_version") or data.get("default_version")
        if not version_info or not version_info.get("id"):
            raise Exception(f"Model {model_ref} did not provide a latest version")

        version_id = version_info["id"]
        self._version_cache[model_ref] = version_id
        return version_id

    def _save_bytes_to_temp(self, blob: bytes) -> str:
        """Persist raw bytes to a temporary PNG file and return the path."""
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        with open(temp_file.name, "wb") as handle:
            handle.write(blob)
        return temp_file.name

    def _first_url_from_output(self, output) -> str:
        """Extract the first URL from various output formats.

        Handles:
        - Iterator of FileOutput objects with .url
        - Iterator of strings
        - List of URLs
        - Single string URL
        - Bytes (base64 encoded images) -> saves to temp and returns local path

        Returns empty string if no valid URL found.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # If it's an iterator, convert to list first to inspect it
        if hasattr(output, '__iter__') and not isinstance(output, (str, bytes, list)):
            try:
                output = list(output)
            except Exception as e:
                logger.debug(f"Failed to convert iterator: {e}")
                pass

        # If it's a list, check first item
        if isinstance(output, list):
            if not output:
                return ""
            first_item = output[0]
            
            # If first item is an object with .url attribute (FileOutput)
            if hasattr(first_item, 'url'):
                return str(first_item.url)
            # If first item is a string URL
            if isinstance(first_item, str):
                return first_item
            # If first item is bytes
            if isinstance(first_item, bytes):
                return self._save_bytes_to_temp(first_item)
            return ""

        # If it's a single string
        if isinstance(output, str):
            return output

        # If it's bytes
        if isinstance(output, bytes):
            return self._save_bytes_to_temp(output)

        # If it has a .url attribute directly
        if hasattr(output, 'url'):
            return str(output.url)

        return ""
    
    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024,
                       aspect_ratio: str = "1:1", output_format: str = "png",
                       output_quality: int = 90, guidance_scale: float = 3.5,
                       num_inference_steps: int = 28, seed: int = -1,
                       num_outputs: int = 1, speed_mode: str = "Extra Juiced 🔥 (more speed)") -> str:
        """Generate an image using prunaai/flux-fast with comprehensive parameter control.

        Args:
            prompt: Image description/prompt
            width: Image width in pixels (256-2048)
            height: Image height in pixels (256-2048)
            aspect_ratio: Aspect ratio override (1:1, 16:9, 9:16, etc.)
            output_format: jpg, png, or webp
            output_quality: Compression quality 1-100 (jpg/webp only)
            guidance_scale: How closely to follow prompt (0-20, recommended 3.5)
            num_inference_steps: Quality vs speed (10-150, default 28)
            seed: Reproducibility seed (-1 for random)
            num_outputs: Generate multiple variations (1-4)
            speed_mode: Speed optimization level

        When use_local is True and a local_manager is supplied, defers to local manager.
        Otherwise calls prunaai/flux-fast (fastest Flux endpoint).
        """
        if self.use_local and self.local_manager:
            return self.local_manager.generate_image_local(prompt, width, height)

        # Flux Fast parameters (comprehensive from Replicate docs)
        input_data = {
            "prompt": prompt,
            "guidance": guidance_scale,  # Flux Fast uses "guidance" not "guidance_scale"
            "image_size": max(width, height),  # Flux Fast uses single "image_size" for longest side
            "aspect_ratio": aspect_ratio,
            "output_format": output_format,
            "output_quality": output_quality,
            "num_inference_steps": num_inference_steps,
            "speed_mode": speed_mode,
        }
        
        # Add seed if specified (Flux Fast uses -1 for random)
        if seed != -1:
            input_data["seed"] = seed
        
        try:
            output = self._run_model(self.image_model, input_data)
            url = self._first_url_from_output(output)
            
            if not url:
                raise Exception(f"No URL extracted from output. Raw output was: {output}")
            
            return url
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}. Check API quota or try a different model.")

    def _process_text_output(self, output: Any) -> str:
        """Helper to process text output from various model return types."""
        if isinstance(output, list):
            return "".join(str(x) for x in output)
        if isinstance(output, Iterable) and not isinstance(output, (str, bytes)):
            return "".join(str(x) for x in output)
        return str(output)

    def generate_text(self, prompt: str, max_tokens: int = 800,
                      temperature: float = 0.7, top_p: float = 0.9,
                      frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
                      system_prompt: Optional[str] = None) -> str:
        """Generate text using openai/gpt-oss-120b model via Replicate with advanced control.

        Args:
            prompt: Input prompt/question
            max_tokens: Maximum response length (50-4096)
            temperature: Creativity level (0=focused, 2=random)
            top_p: Nucleus sampling threshold (0-1)
            frequency_penalty: Reduce repetition (0-2)
            presence_penalty: Encourage new topics (0-2)
            system_prompt: Optional system instruction

        Returns:
            str: Generated text response
        """
        input_data = {
            "prompt": prompt,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty
        }
        if system_prompt:
            # This model might not have a dedicated system_prompt field.
            # Prepending it to the main prompt is a common workaround.
            input_data["prompt"] = f"System: {system_prompt}\n\nUser: {prompt}"

        try:
            output = self._run_model(self.text_model, input_data)
            return self._process_text_output(output)
        except Exception as e:
            # Try fallback model
            import logging
            logging.debug(f"Primary text model failed: {e}. Trying fallback...")
            try:
                fallback_model = "meta/meta-llama-3-70b-instruct"
                output = self._run_model(fallback_model, input_data)
                return self._process_text_output(output)
            except Exception as fallback_error:
                raise Exception(f"Text generation failed with primary and fallback models. Primary: {str(e)}. Fallback: {str(fallback_error)}. Check API quota.")

    def generate_text_fast(self, prompt: str, max_tokens: int = 400,
                           temperature: float = 0.7, system_prompt: Optional[str] = None) -> str:
        """Generate text using fast Llama 3 8B model for speed-critical operations.
        
        This is 3-5x faster than the default Claude model, ideal for "fast mode" generation.

        Args:
            prompt: Input prompt/question
            max_tokens: Maximum response length (reduced for speed)
            temperature: Creativity level (0=focused, 2=random)
            system_prompt: Optional system instruction

        Returns:
            str: Generated text response
        """
        input_data = {
            "prompt": prompt,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            input_data["prompt"] = f"System: {system_prompt}\n\nUser: {prompt}"

        try:
            output = self._run_model(self.FAST_TEXT_MODEL, input_data)
            return self._process_text_output(output)
        except Exception as e:
            # Fallback to 70B model if 8B fails
            import logging
            logging.debug(f"Fast text model failed: {e}. Trying 70B fallback...")
            try:
                fallback_model = "meta/meta-llama-3-70b-instruct"
                output = self._run_model(fallback_model, input_data)
                return self._process_text_output(output)
            except Exception as fallback_error:
                raise Exception(f"Fast text generation failed. Error: {str(fallback_error)}")

    def analyze_image(self, image_b64: str, prompt: str = "Describe this image in detail.") -> str:
        """Analyze an image using a vision-language model.
        
        Uses Salesforce BLIP for image captioning/analysis.
        
        Args:
            image_b64: Base64 encoded image data
            prompt: Question or instruction about the image
            
        Returns:
            str: Text description/analysis of the image
        """
        # Use Salesforce BLIP-2 for vision analysis (reliable model)
        vision_model = "salesforce/blip"
        
        # Create data URL from base64
        image_url = f"data:image/png;base64,{image_b64}"
        
        input_data = {
            "image": image_url,
            "task": "visual_question_answering",
            "question": prompt
        }
        
        try:
            output = self._run_model(vision_model, input_data)
            return self._process_text_output(output)
        except Exception as e:
            # Try image captioning as fallback
            import logging
            logging.debug(f"VQA failed: {e}. Trying caption mode...")
            try:
                input_data = {
                    "image": image_url,
                    "task": "image_captioning"
                }
                output = self._run_model(vision_model, input_data)
                return self._process_text_output(output)
            except Exception as fallback_error:
                raise Exception(f"Image analysis failed: {str(fallback_error)}")

    def generate_video(self, prompt: Optional[str] = None, image_url: Optional[str] = None,
                       image_path: Optional[str] = None, aspect_ratio: str = "16:9", 
                       motion_level: int = 4) -> str:
        """Generate a short video using kwaivgi/kling-v2.5-turbo-pro.

        Either a prompt, image_url, or image_path can be provided.
        
        Args:
            prompt: Text description for video generation
            image_url: URL of image to use as reference (deprecated, use image_path)
            image_path: Local path to image file (preferred - Replicate handles upload)
            aspect_ratio: Video aspect ratio
            motion_level: Amount of motion (1-5, lower is subtle)
            
        Returns:
            URL of generated video
        """
        if not prompt and not image_url and not image_path:
            raise ValueError("Either 'prompt', 'image_url', or 'image_path' must be provided for video generation.")

        input_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "motion_level": motion_level, # Lower is less motion, higher is more
        }

        # Prefer image_path (file object) over image_url
        if image_path:
            # Note: Kling uses "image" parameter, not "image_url"
            # When using replicate.run() directly, we'll pass the file object
            input_data["image_path"] = image_path
        elif image_url:
            # Fallback to URL (for backward compatibility)
            input_data["image_url"] = image_url
        # else: text-to-video only mode

        try:
            output = self._run_model(self.video_model, input_data)
            return self._first_url_from_output(output)
        except Exception as e:
            raise Exception(f"Video generation failed: {str(e)}. Note: Video generation is expensive and may require quota.")

    def generate_speech(self, text: str, voice_id: str = "English_Trustworth_Man",
                        speed: float = 1.0, pitch: int = 0, volume: float = 1.0,
                        emotion: str = "neutral", sample_rate: str = "44100",
                        audio_format: str = "mp3") -> str:
        """Generate speech audio using minimax/speech-02-hd with full parameter control.
        
        Args:
            text: Text to synthesize
            voice_id: Voice preset (e.g., "English_Trustworth_Man", "English_CalmWoman")
            speed: Speech rate multiplier (0.5-2.0)
            pitch: Pitch shift in semitones (-10 to +10)
            volume: Audio volume multiplier (0.0-2.0)
            emotion: Emotional tone (neutral, happy, sad, excited, calm, angry, fearful)
            sample_rate: Audio quality in Hz (16000, 22050, 24000, 44100, 48000)
            audio_format: Output format (mp3, wav, flac)
        
        Returns:
            str: URL to generated audio file
        """
        input_data = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "vol": volume,
            "emotion": emotion,
            "audio_sample_rate": int(sample_rate),
            "format": audio_format
        }
        output = self._run_model(self.speech_model, input_data)
        return self._first_url_from_output(output)
    
    # ========================
    # ControlNet Methods
    # ========================
    
    def generate_canny_map(self, image_url: str, low_threshold: int = 100, 
                          high_threshold: int = 200) -> str:
        """Generate Canny edge map for product outline control.
        
        Args:
            image_url: URL of product image
            low_threshold: Lower threshold for edge detection (0-255)
            high_threshold: Upper threshold for edge detection (0-255)
            
        Returns:
            URL of generated edge map (black background, white edges)
        """
        input_data = {
            "image": image_url,
            "low_threshold": low_threshold,
            "high_threshold": high_threshold
        }
        try:
            output = self._run_model(self.DEFAULT_CANNY_MODEL, input_data)
            return self._first_url_from_output(output)
        except Exception as e:
            raise Exception(f"Canny edge map generation failed: {str(e)}")
    
    def generate_depth_map(self, image_url: str, model_type: str = "dpt_large") -> str:
        """Generate depth map for 3D structure control.
        
        Args:
            image_url: URL of product image
            model_type: MiDaS model type ("dpt_large", "dpt_hybrid", "midas_small")
            
        Returns:
            URL of generated depth map (grayscale where brightness = distance)
        """
        input_data = {
            "image": image_url,
            "model_type": model_type
        }
        try:
            output = self._run_model(self.DEFAULT_DEPTH_MODEL, input_data)
            return self._first_url_from_output(output)
        except Exception as e:
            raise Exception(f"Depth map generation failed: {str(e)}")
    
    def generate_multi_controlnet_image(
        self,
        prompt: str,
        control_image_1: str,
        control_type_1: str,
        conditioning_scale_1: float,
        control_image_2: Optional[str] = None,
        control_type_2: Optional[str] = None,
        conditioning_scale_2: Optional[float] = None,
        control_image_3: Optional[str] = None,
        control_type_3: Optional[str] = None,
        conditioning_scale_3: Optional[float] = None,
        negative_prompt: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 30,
        seed: int = -1
    ) -> str:
        """Generate image with multiple ControlNet controls simultaneously.
        
        This allows locking product shape (canny), depth (depth map), and region (semantic mask)
        all at once for maximum control and consistency.
        
        Args:
            prompt: Text description of desired output scene
            control_image_1: URL of first control map (required)
            control_type_1: Type of first control ("canny", "depth", "seg", "normal", etc.)
            conditioning_scale_1: Strength of first control (0.0-1.0, higher = stronger)
            control_image_2: URL of second control map (optional)
            control_type_2: Type of second control
            conditioning_scale_2: Strength of second control
            control_image_3: URL of third control map (optional)
            control_type_3: Type of third control
            conditioning_scale_3: Strength of third control
            negative_prompt: What to avoid in generation
            width: Output width
            height: Output height
            guidance_scale: How closely to follow prompt (3-15, typical 7-8)
            num_inference_steps: Quality vs speed (20-50, more = better quality)
            seed: Random seed for reproducibility (-1 = random)
            
        Returns:
            URL of generated image with all controls applied
            
        Example:
            >>> # Generate product in new environment while maintaining shape
            >>> url = api.generate_multi_controlnet_image(
            ...     prompt="luxury product on marble pedestal, studio lighting",
            ...     control_image_1=canny_edge_map_url,  # Product outline
            ...     control_type_1="canny",
            ...     conditioning_scale_1=0.85,  # Strong lock on shape
            ...     control_image_2=depth_map_url,  # Scene depth
            ...     control_type_2="depth",
            ...     conditioning_scale_2=0.6,  # Medium depth influence
            ...     negative_prompt="distorted, warped, blurry"
            ... )
        """
        input_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, distorted, low quality, warped product",
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
            "seed": seed,
            
            # First control (required)
            "control_image_1": control_image_1,
            "control_type_1": control_type_1,
            "controlnet_conditioning_scale_1": conditioning_scale_1,
        }
        
        # Add optional second control
        if control_image_2 and control_type_2 is not None and conditioning_scale_2 is not None:
            input_data["control_image_2"] = control_image_2
            input_data["control_type_2"] = control_type_2
            input_data["controlnet_conditioning_scale_2"] = conditioning_scale_2
        
        # Add optional third control
        if control_image_3 and control_type_3 is not None and conditioning_scale_3 is not None:
            input_data["control_image_3"] = control_image_3
            input_data["control_type_3"] = control_type_3
            input_data["control_conditioning_scale_3"] = conditioning_scale_3
        
        try:
            output = self._run_model(self.DEFAULT_MULTI_CONTROLNET_MODEL, input_data)
            return self._first_url_from_output(output)
        except Exception as e:
            raise Exception(f"Multi-ControlNet image generation failed: {str(e)}")
    
    def apply_style_control(
        self,
        image_url: str,
        style_reference_url: str,
        prompt: str,
        style_strength: float = 0.7,
        guidance_scale: float = 8.0,
        num_inference_steps: int = 30
    ) -> str:
        """Apply consistent brand visual style to an image using ControlNet.
        
        Args:
            image_url: URL of image to apply style to
            style_reference_url: URL of reference image with desired brand aesthetic
            prompt: Text prompt for the styled output
            style_strength: How strongly to apply style (0.0-1.0)
            guidance_scale: Prompt adherence
            num_inference_steps: Quality
            
        Returns:
            URL of image with style applied
            
        Example:
            >>> # Apply brand look to generated product scene
            >>> styled = api.apply_style_control(
            ...     image_url=generated_scene_url,
            ...     style_reference_url=brand_reference_url,
            ...     prompt="maintain product placement, apply brand aesthetic",
            ...     style_strength=0.7
            ... )
        """
        input_data = {
            "image": image_url,
            "style_image": style_reference_url,
            "prompt": prompt,
            "style_strength": style_strength,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps
        }
        
        try:
            output = self._run_model(self.DEFAULT_STYLE_CONTROLNET_MODEL, input_data)
            return self._first_url_from_output(output)
        except Exception as e:
            raise Exception(f"Style control application failed: {str(e)}")
