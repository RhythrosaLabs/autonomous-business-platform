# autonomous-pipeline

Fully autonomous end-to-end campaign pipeline. One command delivers every asset: strategy brief, image prompt (+ real image if Replicate key is present), product copy, video script (+ video spec), social posts, email campaign, hashtags, and a publish checklist — all saved to a file.

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

## PHASE 0 — Parse & API check

Parse `$ARGUMENTS`: extract **concept** (text before first `--`), `--workflow` override, `--brand` name.

Run this silently:
```bash
python scripts/pipeline_runner.py --step check
```

Store the result:
- `API_KEY_PRESENT` → set `has_api=true`. Real images and video specs will be generated via Replicate.
- `NO_API_KEY` → set `has_api=false`. Write production-ready prompts as the deliverable instead.

If `--brand` given, read `brand_templates.json`, find the matching template (case-insensitive on `name`), extract: `voice`, `content_tone`, `image_style`, `colors.primary`, `colors.secondary`, `cta_text`, `hashtags`. If not found, continue without brand context.

Print: `🚀 Pipeline starting: "<concept>" | API: <yes/no> | Brand: <name or none>`

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

**If `has_api=true`**, immediately run:
```bash
python scripts/pipeline_runner.py --step image \
  --prompt "<the exact prompt above>" \
  --output-dir "data/pipeline_runs"
```
Print the returned `IMAGE_URL:…` or `IMAGE_FILE:…` line as the image result.

**If `has_api=false`**, the prompt block above is the deliverable. Note: "Ready to submit to Replicate when API key is configured."

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

**If `has_api=true`** and `image_url` is in context, run:
```bash
python scripts/pipeline_runner.py --step video \
  --prompt "<video prompt above>" \
  --image-url "<image_url>" \
  --aspect-ratio "16:9"
```
Print the returned `VIDEO_URL:…` as the video result.

**If `has_api=false`** or no `image_url`, the spec above is the deliverable.

---

## PHASE 4 — Email campaign

Always execute this phase regardless of workflow.

Write a complete HTML email. Output subject line and preview text above the code block, then the full HTML inside a fenced block. Requirements: inline styles only, max-width 600px, hero section referencing the design, product copy from `product_description`, prominent CTA button using `cta_text` or "Shop Now", footer with `{{ unsubscribe_url }}` placeholder.

---

## PHASE 5 — Save to file

1. Build filename: lowercase concept, first 40 chars, spaces→underscores, strip special chars, append `_YYYYMMDD`. Example: `cyberpunk_neon_husky_with_glowing_eyes_20260527.md`
2. Use the Write tool to create `data/pipeline_runs/<filename>` containing every generated asset with `##` headings.
3. Print: `💾 Saved → data/pipeline_runs/<filename>`

---

## PHASE 6 — Summary & publish checklist

```
## Campaign Complete
Concept:   <concept>
Workflow:  <type>
Brand:     <name or none>
API:       <real assets generated / prompts only>
Output:    data/pipeline_runs/<filename>

Assets produced:
✅ Strategy Brief
✅/⬜ Design image (generated / prompt ready)
✅/⬜ Product description
✅/⬜ Video script
✅/⬜ Video (generated / spec ready)
✅/⬜ Social posts (Twitter · Instagram · Facebook)
✅/⬜ Marketing copy
✅/⬜ Tags
✅/⬜ Email campaign
✅/⬜ Hashtags
```

Then print the full publish checklist:

```markdown
## Publish Checklist

### Now
- [ ] Printify/Printful — submit Image Generation Prompt → generate mockup → upload to store
- [ ] Twitter/X — post the Twitter entry from Social Posts
- [ ] Instagram — post with mockup image + caption from Social Posts

### Within 24 hours
- [ ] Shopify Product — product description + tags → new product listing
- [ ] Facebook — schedule the Facebook post
- [ ] Email — paste HTML email into Klaviyo/Shopify Email → send to list

### Within 48 hours
- [ ] YouTube — generate video using Video Generation Spec → upload, use thumbnail prompt
- [ ] Blog — paste full article into Shopify Blog → publish
- [ ] Pinterest — use social image prompt → pin linking to product

### Ongoing
- [ ] Reuse hashtag set across weekly posts
- [ ] A/B test headline variants from Marketing Copy
- [ ] Review email CTR at 48 hours
```
