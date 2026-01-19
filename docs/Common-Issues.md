# Common Issues & Troubleshooting

Quick solutions to common problems you might encounter.

## 🔑 API Key Issues

### "API key not found" Error

**Symptom:** Application requests API key even after entering it.

**Solutions:**

1. **Check key format:**
   ```python
   # OpenAI keys start with: sk-
   # Anthropic keys start with: sk-ant-
   # Replicate keys start with: r8_
   ```

2. **Verify key storage:**
   ```python
   import streamlit as st
   # Check session state
   if 'user_openai_api_key' in st.session_state:
       print("✓ Key stored")
   else:
       print("✗ Key not found - re-enter in Settings")
   ```

3. **Use environment variables:**
   ```bash
   # Add to .env file
   OPENAI_API_KEY=sk-your-actual-key
   ANTHROPIC_API_KEY=sk-ant-your-actual-key
   ```

4. **Restart application:**
   - Close browser tab completely
   - Stop server (Ctrl+C)
   - Clear browser cache
   - Restart: `streamlit run autonomous_business_platform.py`

### API Rate Limits

**Symptom:** "Rate limit exceeded" errors

**Solutions:**

1. **Check your API quota:**
   - OpenAI: platform.openai.com/account/usage
   - Anthropic: console.anthropic.com/settings/limits
   - Replicate: replicate.com/account

2. **Implement delays:**
   ```python
   import time
   for i in range(10):
       result = generate_image(prompt)
       time.sleep(2)  # Wait 2 seconds between requests
   ```

3. **Use caching:**
   ```python
   import streamlit as st
   
   @st.cache_data(ttl=3600)  # Cache for 1 hour
   def expensive_api_call(prompt):
       return api.generate(prompt)
   ```

## 🚫 Import Errors

### "ModuleNotFoundError"

**Symptom:** `ModuleNotFoundError: No module named 'app.services.xxx'`

**Solutions:**

1. **Verify file structure:**
   ```bash
   ls -la app/services/  # Check if file exists
   ls -la app/tabs/      # Check tabs
   ls -la app/utils/     # Check utils
   ```

2. **Check Python path:**
   ```python
   import sys
   print(sys.path)  # Should include your project root
   ```

3. **Use absolute imports:**
   ```python
   # ✓ Correct
   from app.services.ai_twitter_poster import TwitterPoster
   
   # ✗ Avoid
   from ai_twitter_poster import TwitterPoster
   ```

4. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

### "Cannot import name 'xxx'"

**Symptom:** `ImportError: cannot import name 'function_name'`

**Solutions:**

1. **Check function exists:**
   ```bash
   grep -n "def function_name" app/services/*.py
   ```

2. **Verify spelling:**
   - Python is case-sensitive
   - `get_api_key` ≠ `get_API_key`

3. **Check circular imports:**
   ```python
   # If A imports B and B imports A = circular import
   # Solution: Move shared code to separate module
   ```

## 🎨 Image Generation Issues

### "Image generation failed"

**Symptom:** Images don't generate or return errors

**Solutions:**

1. **Check prompt length:**
   ```python
   # Keep prompts under 500 characters
   prompt = "A beautiful sunset"  # ✓ Good
   prompt = "A very detailed..."   # ✗ Too long
   ```

2. **Verify model availability:**
   ```python
   # Test with simple prompt
   from app.services.flux_static_ads_generator import generate_image
   
   result = generate_image("test")
   if result:
       print("✓ Model working")
   ```

3. **Check Replicate credits:**
   - Go to replicate.com/account
   - Add payment method if needed
   - Free tier has limits

4. **Try different model:**
   ```python
   # If FLUX fails, try SDXL
   model = "stability-ai/sdxl:xxxxx"
   ```

### Images Look Wrong

**Symptom:** Generated images don't match expectations

**Solutions:**

1. **Improve prompt engineering:**
   ```python
   # ✗ Vague
   prompt = "product photo"
   
   # ✓ Specific
   prompt = "professional product photo, white background, 
            centered, studio lighting, high resolution"
   ```

2. **Adjust parameters:**
   ```python
   generate_image(
       prompt="...",
       guidance_scale=7.5,  # Lower = more creative, Higher = follow prompt
       num_inference_steps=50,  # More steps = better quality
       width=1024,
       height=1024
   )
   ```

3. **Use negative prompts:**
   ```python
   negative_prompt = "blurry, low quality, distorted, watermark"
   ```

## 📹 Video Generation Issues

### "Video processing stuck"

**Symptom:** Videos never finish generating

**Solutions:**

1. **Check video length:**
   ```python
   # Keep videos under 10 seconds for faster processing
   duration = 3  # seconds - recommended
   ```

2. **Monitor progress:**
   ```python
   import replicate
   
   prediction = replicate.predictions.create(...)
   while prediction.status != "succeeded":
       print(f"Status: {prediction.status}")
       time.sleep(5)
       prediction.reload()
   ```

3. **Simplify prompt:**
   ```python
   # ✗ Complex
   prompt = "Camera pans across detailed cityscape with..."
   
   # ✓ Simple
   prompt = "Camera slowly zooms into product"
   ```

## 🏪 E-commerce Integration Issues

### Shopify Connection Failed

**Symptom:** Can't connect to Shopify store

**Solutions:**

1. **Verify credentials:**
   ```python
   # Check format
   store_url = "your-store.myshopify.com"  # ✓ Include .myshopify.com
   api_key = "..."  # From Shopify Admin API
   ```

2. **Check API scopes:**
   - Need: `read_products`, `write_products`
   - Grant in Shopify Admin → Apps → Your App

3. **Test connection:**
   ```python
   from app.services.shopify_service import ShopifyService
   
   shop = ShopifyService()
   try:
       products = shop.list_products()
       print(f"✓ Connected: {len(products)} products")
   except Exception as e:
       print(f"✗ Error: {e}")
   ```

### Printify Upload Failed

**Symptom:** Can't upload designs to Printify

**Solutions:**

1. **Check image format:**
   ```python
   # Supported: PNG, JPG, JPEG
   # Max size: 25MB
   # Min resolution: 300 DPI
   ```

2. **Verify shop ID:**
   ```python
   from app.services.printify import PrintifyService
   
   ps = PrintifyService()
   shops = ps.get_shops()
   print(f"Available shops: {shops}")
   ```

3. **Check API token:**
   - Token format: alphanumeric string
   - Get from: Printify Dashboard → Connections → API

## 💬 Chat/Otto Issues

### Otto Not Responding

**Symptom:** Otto doesn't reply or times out

**Solutions:**

1. **Check Claude API:**
   ```python
   # Verify key works
   import anthropic
   
   client = anthropic.Anthropic(api_key="sk-ant-...")
   message = client.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=100,
       messages=[{"role": "user", "content": "Hi"}]
   )
   print(message.content)
   ```

2. **Reduce context length:**
   ```python
   # Clear conversation history
   if len(st.session_state.messages) > 20:
       st.session_state.messages = st.session_state.messages[-10:]
   ```

3. **Check timeout settings:**
   ```python
   import httpx
   
   client = anthropic.Anthropic(
       timeout=httpx.Timeout(60.0, connect=5.0)
   )
   ```

### Slash Commands Not Working

**Symptom:** `/command` doesn't trigger action

**Solutions:**

1. **Check command format:**
   ```python
   # ✓ Correct
   /image a beautiful sunset
   
   # ✗ Wrong
   / image a beautiful sunset  # No space after /
   /Image a beautiful sunset   # Commands are lowercase
   ```

2. **Verify command exists:**
   ```python
   from app.services.otto_super_engine import SLASH_COMMANDS
   print(SLASH_COMMANDS.keys())  # List all commands
   ```

## 🐛 Application Errors

### "Streamlit Connection Error"

**Symptom:** Page won't load or keeps disconnecting

**Solutions:**

1. **Check port availability:**
   ```bash
   # macOS/Linux
   lsof -i :8501
   
   # Windows
   netstat -ano | findstr :8501
   ```

2. **Kill existing process:**
   ```bash
   # macOS/Linux
   kill -9 $(lsof -t -i:8501)
   
   # Windows
   taskkill /F /PID <PID>
   ```

3. **Use different port:**
   ```bash
   streamlit run autonomous_business_platform.py --server.port 8502
   ```

### "Session State Error"

**Symptom:** Variables not persisting or random resets

**Solutions:**

1. **Initialize in main:**
   ```python
   # At top of autonomous_business_platform.py
   if 'initialized' not in st.session_state:
       st.session_state.initialized = True
       st.session_state.messages = []
       st.session_state.api_keys = {}
   ```

2. **Check for rerun loops:**
   ```python
   # ✗ Causes infinite loop
   if True:
       st.rerun()
   
   # ✓ Conditional rerun
   if condition_met and not st.session_state.rerun_done:
       st.session_state.rerun_done = True
       st.rerun()
   ```

### Memory Errors

**Symptom:** "Out of memory" or application crashes

**Solutions:**

1. **Clear cache:**
   ```python
   import streamlit as st
   
   st.cache_data.clear()
   st.cache_resource.clear()
   ```

2. **Limit batch sizes:**
   ```python
   # ✗ Process 100 images at once
   results = [generate_image(p) for p in prompts]
   
   # ✓ Process in batches of 10
   for i in range(0, len(prompts), 10):
       batch = prompts[i:i+10]
       results.extend([generate_image(p) for p in batch])
   ```

3. **Monitor usage:**
   ```python
   import psutil
   
   process = psutil.Process()
   print(f"Memory: {process.memory_info().rss / 1024**2:.2f} MB")
   ```

## 🔐 Authentication Issues

### Demo Mode Not Working

**Symptom:** API keys visible when Demo Mode enabled

**Solutions:**

1. **Verify setting:**
   ```python
   import streamlit as st
   print(f"Demo Mode: {st.session_state.get('demo_mode', False)}")
   ```

2. **Re-enable:**
   - Go to Settings → Security
   - Toggle Demo Mode OFF then ON
   - Refresh page

### Password Protection

**Symptom:** Need to add password to deployment

**Solutions:**

```python
# Add to autonomous_business_platform.py
import streamlit as st

def check_password():
    """Returns True if password is correct."""
    
    def password_entered():
        if st.session_state["password"] == "your_secure_password":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password",
            on_change=password_entered, key="password"
        )
        return False
    
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password",
            on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    
    else:
        return True

if not check_password():
    st.stop()

# Rest of your app...
```

## 🚀 Performance Issues

### Slow Loading

**Symptom:** Pages take forever to load

**Solutions:**

1. **Enable caching:**
   ```python
   @st.cache_data(ttl=3600)
   def load_data():
       # Expensive operation
       return data
   ```

2. **Lazy load images:**
   ```python
   # Don't load all images at once
   with st.expander("View Images"):
       st.image(images)  # Only loads when expanded
   ```

3. **Use session state:**
   ```python
   # ✗ Recalculates every time
   result = expensive_function()
   
   # ✓ Calculate once
   if 'result' not in st.session_state:
       st.session_state.result = expensive_function()
   result = st.session_state.result
   ```

### High CPU Usage

**Symptom:** Computer slows down when running app

**Solutions:**

1. **Limit concurrent operations:**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=2) as executor:
       results = executor.map(process_item, items)
   ```

2. **Add delays:**
   ```python
   import time
   for item in items:
       process(item)
       time.sleep(0.1)  # Small delay
   ```

## 📝 Getting More Help

Still stuck? Here's how to get help:

1. **Check logs:**
   ```bash
   tail -f logs/app.log
   ```

2. **Enable debug mode:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Create issue:**
   - Go to GitHub Issues
   - Include error message, logs, steps to reproduce

4. **Search existing issues:**
   - Check if someone else had same problem
   - Look for closed issues with solutions

---

**Quick Reference:**
- [Installation Guide](Installation-Guide)
- [Configuration Guide](Configuration)
- [FAQ](FAQ)
- [GitHub Issues](https://github.com/RhythrosaLabs/autonomous-business-platform/issues)
