# autonomous-pipeline

Fully autonomous end-to-end business campaign pipeline. Takes a concept and delivers every asset — design prompt, product copy, video script, social media posts, marketing copy, hashtags, email campaign, blog post, campaign summary, and publish checklist — all written out in full, saved to a file, and presented to the user without any pauses or questions.

**CRITICAL OPERATING RULES — never break these:**
- Do NOT ask the user any questions at any point.
- Do NOT wait for approval between steps.
- Do NOT say "I would generate…" or "this would be sent to…" — write the actual content.
- Do NOT summarize or truncate any output. Write everything in full.
- Do NOT stop early. Run every step in the plan to completion.
- If any information is missing, invent a reasonable value and continue.
- The pipeline runs start to finish in a single turn and delivers everything.

## Usage

```
/autonomous-pipeline <concept> [--workflow <type>] [--brand <template-name>]
```

**Examples:**
```
/autonomous-pipeline "Cyberpunk neon husky with glowing eyes"
/autonomous-pipeline "vintage botanical poster collection" --workflow content_creation
/autonomous-pipeline "retro 80s synthwave aesthetic" --brand HuskyBrand
```

## Arguments

`$ARGUMENTS` — the full argument string passed after the slash command.

- First positional value (quoted or unquoted up to a flag) → the **concept**.
- `--workflow <type>` — override auto-detection. Valid types: `full_campaign_with_video`, `product_campaign`, `video_production`, `content_creation`, `social_media`, `research`, `general`.
- `--brand <name>` — name of a brand template from `brand_templates.json` to inject into all prompts.

If no concept is provided in `$ARGUMENTS`, invent one: pick a creative, commercially viable design theme (e.g. "Mystical wolf and moon watercolor art") and proceed without asking.

---

## Execution

Work through each phase below in strict order. Never skip a phase. Show a progress header before each phase: `## Phase N — <name>`.

---

### Phase 0 — Parse & setup

1. Extract **concept**, **workflow_override**, **brand_name** from `$ARGUMENTS` as described above.
2. If **brand_name** is set, read `brand_templates.json` at the repo root. Find the template whose `name` matches (case-insensitive) and extract: `voice`, `content_tone`, `image_style`, `font_style`, `colors.primary`, `colors.secondary`, `cta_text`, `hashtags`. If the file is missing or the template is not found, continue with no brand context.
3. Print one line: `🚀 Starting autonomous pipeline for: "<concept>"`

---

### Phase 1 — Workflow detection

If `workflow_override` is set, use it.

Otherwise detect from the concept (lowercased):

| Keywords present | Workflow |
|---|---|
| campaign / t-shirt / tshirt / hoodie / poster / product **AND** video / commercial / promo | `full_campaign_with_video` |
| campaign / t-shirt / tshirt / hoodie / poster / product | `product_campaign` |
| video / commercial / animation | `video_production` |
| blog / article / content / write / copy | `content_creation` |
| social / post / twitter / instagram / facebook | `social_media` |
| research / analyze / trend / market | `research` |
| *(none of the above)* | `product_campaign` |

Print: `🧠 Workflow: <type> — <N> steps`

Then print the full step list:
```
Step 1/N — <emoji> <name>
Step 2/N — <emoji> <name>
...
```

---

### Phase 2 — Execute all steps

Run every step for the detected workflow. Use the brand context block in every prompt if a brand was loaded:
```
[Brand: {name} | Voice: {voice} | Tone: {content_tone} | Style: {image_style} | Colors: {primary}/{secondary} | CTA: {cta_text}]
```

Print `### Step N/N — <emoji> <name>` before each step. Execute immediately, output in full.

---

#### Step definitions by workflow

**full_campaign_with_video** — 6 steps:
1. Designer → generate_design
2. Writer → product_description
3. Writer → video_script
4. Video → generate
5. Marketer → social_posts
6. Analyst → summarize

**product_campaign** — 4 steps:
1. Designer → generate_design
2. Writer → product_description
3. Writer → tags
4. Marketer → marketing_copy

**video_production** — 3 steps:
1. Writer → video_script
2. Designer → thumbnail
3. Video → generate

**content_creation** — 4 steps:
1. Researcher → research
2. Writer → outline
3. Writer → full_content
4. Designer → header_image

**social_media** — 3 steps:
1. Marketer → social_posts
2. Designer → social_images
3. Writer → hashtags

**research** — 3 steps:
1. Researcher → deep_research
2. Analyst → analyze
3. Writer → report

**general** — 2 steps:
1. Analyst → analyze_request
2. Writer → respond

---

#### Designer agent — what to output

**generate_design**: Write a complete, production-ready image generation prompt. This is the actual prompt that gets passed to Flux/SDXL — write it as if you are submitting it right now. Be specific: describe composition, lighting, color palette, style, mood, textures, and technical quality markers.

Format:
```
🎨 Image Generation Prompt
──────────────────────────
[Full prompt text — 3-6 sentences, detailed and specific]

Model: black-forest-labs/flux-dev
Resolution: 1024×1024
Aspect ratio: 1:1
Negative prompt: blurry, low quality, watermark, text, cluttered background
```

**thumbnail**: Same format but landscape-oriented, bold and high-contrast for YouTube:
```
Model: black-forest-labs/flux-schnell
Resolution: 1280×720
```

**social_images**: Square format, modern, platform-optimised:
```
Model: black-forest-labs/flux-schnell
Resolution: 1080×1080
```

**header_image**: Wide landscape banner:
```
Model: black-forest-labs/flux-dev
Resolution: 1920×640
```

---

#### Writer agent — what to output

**product_description**: Write 3 full paragraphs of product copy. Paragraph 1: hook and emotional appeal. Paragraph 2: features and what makes it unique. Paragraph 3: lifestyle fit and who it's for. Use brand voice if loaded. Reference the design prompt from context.

**video_script**: Write a complete 30-second video script. Every line must be either `[VISUAL]: <description>` or `[VOICEOVER]: <line>`. Open with a hook visual, build to a product reveal, close with CTA. Include timing notes like `(0:00–0:05)`. Reference the product description from context.

**tags**: Write exactly 10 product tags as a comma-separated list. Mix broad and specific. Example: `neon art, cyberpunk poster, wolf art print, glowing eyes design, dark aesthetic wall art, sci-fi home decor, digital art print, edgy bedroom decor, neon wolf, futuristic art`

**outline**: Write a full content outline with 5 H2 sections. Each section has 3–5 bullet sub-points. Include intro and conclusion sections.

**full_content**: Write a complete 900–1200 word blog post or article using the outline from context as the structure. Use proper H2/H3 markdown headings. No filler — every paragraph must add value.

**hashtags**: Write 15 hashtags in three groups:
- **High-volume (5):** broad, millions of posts
- **Mid-tier (5):** niche but active communities  
- **Niche (5):** specific and highly targeted

**report**: Write a 500–700 word structured report using the research findings from context. Sections: Executive Summary, Key Findings, Market Opportunity, Recommended Actions.

**respond**: Write a thorough, actionable response that fully addresses the concept as a business task.

---

#### Marketer agent — what to output

**social_posts**: Write 3 complete, ready-to-post social media posts. Use this exact format for each:

---
**Platform**: Twitter/X
**Post**: [Full tweet text, ≤280 chars, with 2–3 hashtags inline]
**CTA**: [Link-in-bio CTA or action]

---
**Platform**: Instagram
**Post**: [Full caption, 150–220 words, conversational, story-driven, with 5 hashtags at end]
**CTA**: [e.g. "Link in bio to shop"]

---
**Platform**: Facebook
**Post**: [Full post, 80–120 words, community-focused, with a question to drive comments]
**CTA**: [Direct link or action]

---

Use the product description from context. Use brand hashtags if loaded. Write every word of each post — do not use placeholder text.

**marketing_copy**: Write a complete marketing copy block:
- **Headline**: 6–10 words, punchy and benefit-led
- **Subheadline**: 1 sentence expanding on the headline
- **Bullet 1–3**: Each benefit as a short punchy statement (≤15 words each)
- **CTA**: Button text (3–5 words) — use brand `cta_text` if loaded, otherwise invent one
- **Urgency line**: One short sentence creating FOMO or scarcity

---

#### Researcher agent — what to output

**research / deep_research**: Write a structured research brief with these four sections, each 150–200 words:

1. **Key Insights & Current Trends** — what's happening in this market right now
2. **Target Audience Analysis** — demographics, psychographics, pain points, buying triggers
3. **Competitor Landscape** — name 4–5 real or plausible competitors, their positioning, price points, gaps
4. **Opportunities & Recommendations** — specific, actionable things to do in the next 30 days

---

#### Analyst agent — what to output

**summarize**: List every asset produced in this run with a one-line description of each. Then write a 2–3 sentence overall campaign assessment: what makes this concept strong, what to watch out for, and the single most important next action.

**analyze / analyze_request**: Write 5 specific bullet points covering: business potential, target audience fit, competitive positioning, recommended price point, and top marketing channel.

---

#### Video agent — what to output

Write a complete, ready-to-submit Video Generation Spec. Do not say "this would be submitted" — write it as the actual deliverable:

```
🎬 Video Generation Spec
─────────────────────────
Model:          Kling v2.5 (kwaivgi/kling-v2.5-turbo-pro via Replicate)
Input image:    [Use the image generation prompt from Step 1 to generate the source frame]
Video prompt:   [Write a specific, detailed motion prompt — 2–3 sentences describing
                 exactly how the image should animate: camera movement, subject motion,
                 atmosphere, lighting changes]
Negative prompt: shaky camera, text overlay, watermark, jumpcut, overexposed
Aspect ratio:   16:9
Duration:       5 seconds
Motion level:   3/5
CFG scale:      0.5

Fallback option: Ken Burns effect (free, no API required)
  → zoom: 1.0 → 1.15 over 5 seconds, slow pan right
  → Run: generate_ken_burns_video(image_path, output_path, duration=5)

To generate: paste this spec into the Streamlit dashboard → Video Production tab,
or run: python -m modules.orchestrator with task="{concept}"
```

---

### Phase 3 — Email campaign

Even if not explicitly in the workflow steps, always execute this phase.

Write a complete HTML email campaign for this concept. Output it as a fenced HTML code block. The email must include:
- Subject line (written above the code block)
- Preview text
- Header with product name
- Hero section (describe the image — reference the design prompt)
- 2–3 body sections using the product description copy
- A prominent CTA button using brand CTA text or "Shop Now"
- Footer with unsubscribe link placeholder

Keep it clean and render-safe: inline styles only, max-width 600px, no external CSS.

---

### Phase 4 — Save output file

1. Create `data/pipeline_runs/` if it does not exist.
2. Determine the output filename: take the first 40 characters of the concept, replace spaces with underscores, lowercase, strip special chars. Append today's date as `_YYYYMMDD`. Example: `cyberpunk_neon_husky_with_glowing_eyes_20260527.md`
3. Write a single Markdown file containing every generated asset in order, with clear `##` headings for each section.
4. Use the Write tool to create the file. Do not ask for confirmation.
5. Print: `💾 Saved to: data/pipeline_runs/<filename>`

---

### Phase 5 — Final campaign summary & publish checklist

Print a `## Campaign Complete` section:

```
Concept:   <concept>
Workflow:  <type>
Brand:     <template name or "none">
Steps:     <N> completed / 0 failed
Output:    data/pipeline_runs/<filename>
```

Then list every asset produced with a one-line description.

Then print the full publish checklist — always, for every run:

```markdown
## Publish Checklist

### Immediate (do today)
- [ ] **Printify/Printful**: Submit the Image Generation Prompt → generate mockup → upload to store
- [ ] **Twitter/X**: Copy the Twitter post from Social Posts → post now
- [ ] **Instagram**: Copy the Instagram caption → post with mockup image

### Within 24 hours
- [ ] **Shopify Product**: Use product description + tags → create new product listing
- [ ] **Facebook**: Copy the Facebook post → schedule or post
- [ ] **Email**: Copy the HTML email → paste into Klaviyo/Shopify Email → send to list

### Within 48 hours
- [ ] **YouTube**: Generate the video using the Video Generation Spec → upload with thumbnail prompt
- [ ] **Blog**: Copy the full content → Shopify Blog → new post → publish
- [ ] **Pinterest**: Use the social image prompt → create pin linking to product

### Ongoing
- [ ] Schedule weekly social posts reusing the hashtag set
- [ ] A/B test the two headline variants from marketing copy
- [ ] Track CTR on email campaign after 48 hours
```

End with a single motivating line about the campaign.

---

## Context keys (internal reference)

| Key | Set by | Used by |
|---|---|---|
| `design_prompt` | designer/generate_design | video/generate, writer/video_script |
| `product_description` | writer/product_description | marketer/social_posts, writer/video_script |
| `video_script` | writer/video_script | video/generate |
| `tags` | writer/tags | analyst/summarize |
| `outline` | writer/outline | writer/full_content |
| `full_content` | writer/full_content | analyst/summarize |
| `social_posts` | marketer/social_posts | analyst/summarize |
| `marketing_copy` | marketer/marketing_copy | email, analyst/summarize |
| `hashtags` | writer/hashtags | social_posts, email |
| `research` | researcher | writer/report, analyst/analyze |
| `report` | writer/report | analyst/summarize |
