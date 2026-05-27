---
name: autonomous-pipeline
description: Fully autonomous end-to-end business campaign pipeline. Generates strategy brief, product design prompt, copy, video script, social posts, email campaign, hashtags, and publishes to Printify and Shopify automatically when API keys are configured.
---

# autonomous-pipeline

Fully autonomous end-to-end campaign pipeline. One command delivers every asset: strategy brief, image (generated via Replicate when key is set), product copy, video script + spec, social posts, email campaign, hashtags, a Printify product, a Shopify product draft, a Shopify blog draft, and a publish checklist — all saved to a file.

**NON-NEGOTIABLE RULES:**
- Never pause, ask questions, or wait for approval.
- Never write "I would generate…" — write the actual content.
- Never truncate. Every asset is written in full.
- If anything is missing or ambiguous, invent a reasonable value and continue.
- Run start to finish in a single turn.

## Usage
```
/autonomous-pipeline <concept> [--workflow <type>] [--brand <name>]
```
If no concept is given, invent one and proceed.

---

## PHASE 0 — Parse & platform check

Parse `$ARGUMENTS`: extract **concept** (text before first `--`), `--workflow` override, `--brand` name.

Run platform check:
```bash
python scripts/pipeline_runner.py --step check-platforms
```

Parse the `PLATFORM_STATUS:{...}` JSON line. Store:
- `has_replicate` — Replicate key present (real image/video generation)
- `has_printify`  — Printify key present (auto-create print product)
- `has_shopify`   — Shopify key + URL present (auto-create product listing + blog draft)

If `--brand` given, read `brand_templates.json`, find the matching template (case-insensitive on `name`), extract: `voice`, `content_tone`, `image_style`, `colors.primary`, `colors.secondary`, `cta_text`, `hashtags`. If not found, continue without brand context.

Print one status line:
```
🚀 Pipeline starting: "<concept>"
   Replicate: <yes/no>  |  Printify: <yes/no>  |  Shopify: <yes/no>  |  Brand: <name or none>
```

---

## PHASE 1 — Strategy brief (think before you write)

Before generating any content, reason through the following and write it out as the **Strategy Brief**. This context will shape every asset that follows — do not skip it.

```
## Strategy Brief

**Concept:** <concept>
**Core audience:** <1 sentence — who buys this, their age/identity/motivation>
**Emotional hook:** <the single feeling or desire this concept taps into>
**Positioning:** <1 sentence — how this stands out from generic alternatives>
**Tone of voice:** <3 adjectives, e.g. "bold, irreverent, nostalgic">
**Price point estimate:** <$ range and why>
**Best-fit platforms:** <top 2–3 sales/marketing channels and why>
**Key message (one line):** <the core marketing sentence everything else builds from>
```

Write this section fully. Every content phase below must be consistent with it.

---

## PHASE 2 — Detect workflow

If `--workflow` is set, use it. Otherwise detect from concept keywords:

| Keywords in concept | Workflow |
|---|---|
| (campaign/poster/product/hoodie/tshirt) AND (video/promo/commercial) | `full_campaign_with_video` |
| campaign / poster / product / hoodie / tshirt | `product_campaign` |
| video / commercial / animation | `video_production` |
| blog / article / content / write | `content_creation` |
| social / instagram / twitter / post | `social_media` |
| research / market / trend / analyze | `research` |
| *(default)* | `product_campaign` |

Print: `🧠 Workflow: <type>`

Then print the numbered step list before executing anything.

---

## PHASE 3 — Execute all steps

Print `### Step N/N — <name>` before each step. Use the Strategy Brief as implicit context throughout.

### Step definitions

**full_campaign_with_video:** Design → Product Copy → Video Script → Video → Social Posts → Campaign Summary  
**product_campaign:** Design → Product Copy → Tags → Marketing Copy  
**video_production:** Video Script → Thumbnail → Video  
**content_creation:** Research → Outline → Full Article → Header Image  
**social_media:** Social Posts → Social Images → Hashtags  
**research:** Deep Research → Analysis → Report  
**general:** Analysis → Response  

---

### Designer steps

**generate_design / thumbnail / social_images / header_image**

Write a complete, specific image generation prompt. Be precise about composition, lighting, colour palette, style, mood, and quality markers. Reference the Strategy Brief tone and brand image style if loaded.

Format:
```
🎨 Image Generation Prompt
Model:    prunaai/flux-fast (default) | flux-dev for max quality
Size:     1024×1024 (design/social) | 1280×720 (thumbnail) | 1920×640 (header)
Prompt:   [3–5 sentence detailed prompt]
Negative: blurry, watermark, text overlay, cluttered background, low quality
```

**If `has_replicate=true`**, immediately run:
```bash
python scripts/pipeline_runner.py --step image \
  --prompt "<the exact prompt above>" \
  --output-dir "data/pipeline_runs"
```
Print the returned `IMAGE_URL:…` or `IMAGE_FILE:…` line as the image result.

**If `has_replicate=false`**, the prompt block above is the deliverable. Note: "Ready to submit to Replicate when API key is configured."

Save image URL/path to context as `image_url`.

---

### Writer steps

Write everything in full. Reference the Strategy Brief for tone and audience. Reference earlier context keys where noted.

**product_description** — 3 paragraphs: (1) emotional hook + scene-setting, (2) what it is and what makes it unique, (3) who it's for and lifestyle fit. Use brand voice if loaded. Context: uses `image_url` description. Save as `product_description`.

**video_script** — Complete 30-second script. Every line is `[VISUAL (0:00–0:05)]:` or `[VOICEOVER]:`. Open with hook visual, build to product reveal, close with brand CTA. Reference `product_description`. Save as `video_script`.

**tags** — Exactly 10 comma-separated product tags. Mix broad + niche. Save as `tags`.

**outline** — 5 H2 sections with 3–5 bullet sub-points each, plus intro and conclusion. Save as `outline`.

**full_content** — Full 900–1200 word article/blog post using `outline` as structure. Proper H2/H3 headings. No filler. Save as `full_content`.

**hashtags** — 15 hashtags in three groups (5 high-volume, 5 mid-tier, 5 niche). Use brand hashtags if loaded. Save as `hashtags`.

**report** — 500-word structured report with: Executive Summary, Key Findings, Market Opportunity, Recommended Actions. Uses `research` from context.

---

### Marketer steps

**social_posts** — 3 ready-to-post entries. Write every word — no placeholder text.

---
**Platform**: Twitter/X  
**Post**: [≤280 chars, 2–3 inline hashtags, punchy voice from Strategy Brief]  
**CTA**: [specific action]

---
**Platform**: Instagram  
**Post**: [150–220 word caption, story-driven, 5 hashtags at end]  
**CTA**: [e.g. "Link in bio to shop"]

---
**Platform**: Facebook  
**Post**: [80–120 words, community-focused, ends with engagement question]  
**CTA**: [direct action]

---

Uses `product_description` and `hashtags` from context. Save as `social_posts`.

**marketing_copy** — Headline (≤10 words) · Subheadline (1 sentence) · 3 benefit bullets (≤15 words each) · CTA button text (use brand `cta_text` or invent one) · Urgency line. Save as `marketing_copy`.

---

### Researcher steps

**research / deep_research** — Four sections, 150+ words each: (1) Key Insights & Trends, (2) Target Audience Analysis, (3) Competitor Landscape (4–5 named competitors, price points, gaps), (4) Opportunities & Actions. Save as `research`.

---

### Analyst steps

**summarize** — Bullet list of every asset produced (tick each context key present) then a 3-sentence campaign assessment: what makes this strong, one risk, the single most important next action.

**analyze / analyze_request** — 5 bullets: business potential, audience fit, competitive positioning, recommended price point, top marketing channel.

---

### Video step

**generate**

Write the Video Generation Spec:
```
🎬 Video Generation Spec
Model:          kwaivgi/kling-v2.5-turbo-pro (Kling v2.5)
Source image:   <image_url from context, or "generate design step first">
Video prompt:   [2–3 sentences: exact motion description — camera movement,
                 subject animation, atmosphere, lighting changes]
Negative:       shaky cam, text overlay, jumpcut, overexposed, watermark
Aspect ratio:   16:9
Duration:       5 seconds
Motion level:   3/5
```

**If `has_replicate=true`** and `image_url` is in context, run:
```bash
python scripts/pipeline_runner.py --step video \
  --prompt "<video prompt above>" \
  --image-url "<image_url>" \
  --aspect-ratio "16:9"
```
Print the returned `VIDEO_URL:…` as the video result.

**If `has_replicate=false`** or no `image_url`, the spec above is the deliverable.

---

## PHASE 4 — Email campaign

Always execute this phase regardless of workflow.

Write a complete HTML email. Output subject line and preview text above the code block, then the full HTML inside a fenced block. Requirements: inline styles only, max-width 600px, hero section referencing the design, product copy from `product_description`, prominent CTA button using `cta_text` or "Shop Now", footer with `{{ unsubscribe_url }}` placeholder.

---

## PHASE 5 — Printify product (if `has_printify=true`)

Only run if `has_printify=true`. Otherwise print `⬜ Printify: skipped (no API key)` and continue.

Save the product description to a temp file first, then run:
```bash
# Write description to temp file
# Then:
python scripts/pipeline_runner.py --step printify \
  --image-url "<image_url from context>" \
  --concept "<concept>" \
  --title "<product title derived from concept>" \
  --description-file "/tmp/pipeline_description.txt" \
  --tags "<comma-separated tags from context>" \
  --price-cents 2499 \
  --publish-live
```

Parse the output:
- `PRINTIFY_PRODUCT_ID:xxx` → store as `printify_product_id`
- `PRINTIFY_PUBLISHED:true/false` → store as `printify_published`
- Any `PRINTIFY_ERROR:…` → print the error, continue pipeline

Print: `✅ Printify product created: ID <id> | Published: <yes/no>`

The product type (poster, canvas, t-shirt, etc.) is auto-detected from the concept keywords by the runner — no manual selection needed.

---

## PHASE 6 — Shopify product + blog draft (if `has_shopify=true`)

Only run if `has_shopify=true`. Otherwise print `⬜ Shopify: skipped (no API key / URL)` and continue.

### 6a — Product listing (draft)

Write the product description as HTML to a temp file, then:
```bash
python scripts/pipeline_runner.py --step shopify-product \
  --title "<product title>" \
  --description-file "/tmp/pipeline_description.html" \
  --image-url "<image_url from context>" \
  --tags "<comma-separated tags>"
```

Parse output:
- `SHOPIFY_PRODUCT_ID:xxx` → store as `shopify_product_id`
- `SHOPIFY_PRODUCT_URL:xxx` → store as `shopify_product_url`

Print: `✅ Shopify product draft: <shopify_product_url>`

### 6b — Blog post (draft)

Convert `full_content` markdown to basic HTML (wrap paragraphs in `<p>`, headings in `<h2>`/`<h3>`). Write to temp file, then:
```bash
python scripts/pipeline_runner.py --step shopify-blog \
  --title "<blog post title derived from concept>" \
  --description-file "/tmp/pipeline_blog.html" \
  --image-url "<image_url from context>" \
  --tags "<comma-separated tags>"
```
Note: `--published` flag is NOT passed — all blog posts save as drafts for review.

Parse output:
- `SHOPIFY_BLOG_ID:xxx` → store as `shopify_blog_id`
- `SHOPIFY_BLOG_URL:xxx` → store as `shopify_blog_url`
- `SHOPIFY_BLOG_STATUS:draft` → confirm draft status

Print: `✅ Shopify blog draft saved: <shopify_blog_url>`

---

## PHASE 7 — Save to file

1. Build filename: lowercase concept, first 40 chars, spaces→underscores, strip special chars, append `_YYYYMMDD`. Example: `cyberpunk_neon_husky_with_glowing_eyes_20260527.md`
2. Use the Write tool to create `data/pipeline_runs/<filename>` containing every generated asset with `##` headings.
3. Print: `💾 Saved → data/pipeline_runs/<filename>`

---

## PHASE 8 — Summary & publish checklist

Print the campaign summary using real values from context:

```
## Campaign Complete
Concept:   <concept>
Workflow:  <type>
Brand:     <name or none>
Output:    data/pipeline_runs/<filename>

Assets produced:
✅ Strategy Brief
✅/⬜ Design image          — generated via Replicate / prompt ready
✅/⬜ Product description   — written
✅/⬜ Video script          — written
✅/⬜ Video                 — generated / spec ready
✅/⬜ Social posts          — Twitter · Instagram · Facebook
✅/⬜ Marketing copy        — headline + bullets + CTA
✅/⬜ Tags                  — 10 product tags
✅/⬜ Email campaign        — full HTML ready
✅/⬜ Hashtags              — 15 tags (3 tiers)
✅/⬜ Printify product      — ID: <printify_product_id or "skipped">
✅/⬜ Shopify product draft — <shopify_product_url or "skipped">
✅/⬜ Shopify blog draft    — <shopify_blog_url or "skipped">
```

Then print the publish checklist. Tick off items that were already completed automatically:

```markdown
## Publish Checklist

### Done automatically ✅ (if keys were configured)
- [x/] Printify product — created and published to Shopify store
- [x/] Shopify product listing — created as draft (review in Shopify Admin → Products)
- [x/] Shopify blog post — saved as draft (review in Shopify Admin → Blog Posts → publish when ready)

### Post now
- [ ] Twitter/X — copy the Twitter post from Social Posts
- [ ] Instagram — post with mockup image + caption from Social Posts

### Within 24 hours
- [ ] Facebook — schedule the Facebook post
- [ ] Email — paste HTML email into Klaviyo/Shopify Email → send to list
- [ ] Activate Shopify product draft (Admin → Products → set to Active)

### Within 48 hours
- [ ] YouTube — generate video using Video Generation Spec → upload, use thumbnail prompt
- [ ] Publish Shopify blog draft when ready (Admin → Blog Posts)
- [ ] Pinterest — use social image prompt → pin linking to product

### Ongoing
- [ ] Reuse hashtag set across weekly posts
- [ ] A/B test headline variants from Marketing Copy
- [ ] Review email CTR at 48 hours
```
