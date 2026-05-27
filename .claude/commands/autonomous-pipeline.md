# autonomous-pipeline

Run the full autonomous business pipeline from a single concept. Mirrors the dashboard's MultiAgentOrchestrator: detects workflow type, chains specialized agents, and produces every asset in sequence — design prompt, product copy, video script, social posts, email copy, hashtags, and a final campaign summary. Outputs are saved to `data/pipeline_runs/`.

## Usage

```
/autonomous-pipeline <concept> [--workflow <type>] [--brand <template-name>] [--publish]
```

**Examples:**
```
/autonomous-pipeline "Cyberpunk neon husky with glowing eyes"
/autonomous-pipeline "vintage botanical poster collection" --workflow content_creation
/autonomous-pipeline "retro 80s synthwave aesthetic" --brand HuskyBrand --publish
```

## Arguments

`$ARGUMENTS` — the full argument string passed after the slash command.

- First positional value (quoted or unquoted up to a flag) → the **concept**.
- `--workflow <type>` — override auto-detection. Valid types: `full_campaign_with_video`, `product_campaign`, `video_production`, `content_creation`, `social_media`, `research`, `general`.
- `--brand <name>` — name of a brand template from `brand_templates.json` to inject into all prompts.
- `--publish` — after generation, append Shopify/YouTube/social publish instructions to the summary.

---

## Instructions

Follow each phase below in order. Do not skip phases. For every piece of generated content, write it out in full — do not summarize or truncate.

### Phase 0 — Parse arguments

Extract from `$ARGUMENTS`:
1. **concept** — everything before the first `--` flag (trim surrounding quotes).
2. **workflow_override** — value after `--workflow`, or empty.
3. **brand_name** — value after `--brand`, or empty.
4. **publish_flag** — true if `--publish` present, else false.

If no concept is provided, ask the user: "What concept should I build a campaign around?"

### Phase 1 — Load brand template (if requested)

If `brand_name` is set, read `brand_templates.json` at the repo root. Find the template whose `name` matches (case-insensitive). Extract:
- `voice`, `content_tone`, `image_style`, `font_style`, `colors.primary`, `colors.secondary`, `cta_text`, `hashtags`.

Prepend this brand context block to all prompts in subsequent phases:

```
[Brand: {name} | Voice: {voice} | Tone: {content_tone} | Style: {image_style} | Colors: {primary}/{secondary} | CTA: {cta_text}]
```

If the file is missing or the template is not found, continue without brand context and note it.

### Phase 2 — Detect workflow type

If `workflow_override` is set, use it directly.

Otherwise scan the concept (lowercased) using the same keyword logic as `modules/orchestrator.py`:

| Keywords present in concept | Workflow |
|---|---|
| campaign / t-shirt / tshirt / hoodie / poster / product **AND** video / commercial / promo | `full_campaign_with_video` |
| campaign / t-shirt / tshirt / hoodie / poster / product | `product_campaign` |
| video / commercial / animation | `video_production` |
| blog / article / content / write / copy | `content_creation` |
| social / post / twitter / instagram / facebook | `social_media` |
| research / analyze / trend / market | `research` |
| *(none of the above)* | `general` |

State the detected workflow clearly: `🧠 Workflow detected: <type> — <N> steps`.

### Phase 3 — Build execution plan

Map the workflow to its step sequence (matching `_build_execution_plan` in the orchestrator):

**full_campaign_with_video** (6 steps):
1. Designer → generate_design
2. Writer → product_description
3. Writer → video_script
4. Video → generate
5. Marketer → social_posts
6. Analyst → summarize

**product_campaign** (4 steps):
1. Designer → generate_design
2. Writer → product_description
3. Writer → tags
4. Marketer → marketing_copy

**video_production** (3 steps):
1. Writer → video_script
2. Designer → thumbnail
3. Video → generate

**content_creation** (4 steps):
1. Researcher → research
2. Writer → outline
3. Writer → full_content
4. Designer → header_image

**social_media** (3 steps):
1. Marketer → social_posts
2. Designer → social_images
3. Writer → hashtags

**research** (3 steps):
1. Researcher → deep_research
2. Analyst → analyze
3. Writer → report

**general** (2 steps):
1. Analyst → analyze_request
2. Writer → respond

Print the plan as a numbered list before executing.

### Phase 4 — Execute each step

Work through each step sequentially. Show a header for each step: `### Step N/N — <emoji> <name>`.

For each step, follow the agent instructions below. Pass the output of each step as context to subsequent steps where indicated (context chaining mirrors the orchestrator's `context_updates`).

---

#### Designer agent

**generate_design**
Write a detailed image-generation prompt (suitable for Flux/SDXL) that would produce a commercial-ready product design:
```
Professional product design: {concept} {brand_context}
High quality, commercial ready, clean background, centered composition.
```
Output a `design_prompt` block and note that this would be sent to `black-forest-labs/flux-dev` at 1024×1024. Save as context key `generated_image_prompt`.

**thumbnail**
Write a YouTube-thumbnail-style prompt:
```
YouTube thumbnail style: {concept} {brand_context}. Bold, eye-catching, vibrant colors.
```

**social_images**
Write a square social-media image prompt:
```
Social media post image: {concept} {brand_context}. Square format, modern, engaging.
```

**header_image**
Write a wide blog-header image prompt:
```
Blog header image: {concept} {brand_context}. Wide format, professional, clean.
```

---

#### Writer agent

**product_description**
Write 2–3 paragraphs of compelling product copy. Focus on benefits, features, and emotional appeal. Use brand voice if available. Use the design prompt from context if present. Save as context key `product_description`.

**video_script**
Write a complete 30-second video script. Include `[VISUAL]` cues and `[VOICEOVER]` lines. Reference the product description from context if present. Save as context key `video_script`.

**tags**
Generate exactly 10 relevant product tags/keywords as a comma-separated list. Save as context key `tags`.

**outline**
Create a detailed blog/content outline with H2 sections and bullet-point sub-items. Save as context key `outline`.

**full_content**
Write the full blog post or article (800–1200 words). Use the outline from context as the structure. Save as context key `full_content`.

**hashtags**
Generate 15 hashtags — mix of broad and niche. Group them: 5 high-volume, 5 mid-tier, 5 niche. Save as context key `hashtags`.

**report**
Write a 400–600 word report summarising the research findings from context key `research`. Include key insights, opportunities, and recommended next steps. Save as context key `report`.

**respond**
Provide a helpful, detailed response to the concept as a general task.

---

#### Marketer agent

**social_posts**
Create 3 platform-specific social media posts in this exact format for each:

```
**Platform**: Twitter / Instagram / Facebook
**Post**: [post text]
**CTA**: [call to action]
```

Use the product description from context if present. Use brand hashtags if loaded. Save as context key `social_posts`.

**marketing_copy**
Write a full marketing copy block:
- Headline (punchy, ≤10 words)
- Subheadline (benefit-focused, 1 sentence)
- 3 bullet points highlighting key benefits
- CTA button text

Use brand CTA text if loaded. Save as context key `marketing_copy`.

---

#### Researcher agent

**research / deep_research**
Produce a structured research brief with four sections:
1. Key insights and current trends
2. Target audience analysis (demographics, psychographics, pain points)
3. Competitor landscape overview (3–5 competitors or comparable products)
4. Opportunities and actionable recommendations

Save as context key `research`.

---

#### Analyst agent

**summarize**
Enumerate every asset produced in this run using the context keys present:
- ✅ Design prompt (if `generated_image_prompt` in context)
- ✅ Product description (if `product_description` in context)
- ✅ Video script (if `video_script` in context)
- ✅ Video generation spec (if video step completed)
- ✅ Social media posts (if `social_posts` in context)
- ✅ Marketing copy (if `marketing_copy` in context)
- ✅ Product tags (if `tags` in context)

**analyze / analyze_request**
Provide a concise analysis (3–5 bullet points) of the concept's business potential, target audience, and recommended positioning.

---

#### Video agent

**generate**
The video step does not generate a video in this skill (no Replicate API call possible here). Instead:

1. Confirm that `generated_image_prompt` is in context; if not, warn that design step must run first.
2. Output a **Video Generation Spec** block:

```
Video Generation Spec
─────────────────────
Model:        Kling v2.5 (default) — override with --workflow video_production + task keyword
Input image:  [result of design step would be passed here]
Prompt:       Gentle motion, professional product showcase: {concept}
Aspect ratio: 16:9
Motion level: 3/5
Duration:     5 seconds
Fallback:     Ken Burns effect (free, instant) if API unavailable
```

3. Note: "Run `python -m modules.orchestrator` or trigger from the Streamlit dashboard to generate the actual video via Replicate."

---

### Phase 5 — Save outputs

After all steps complete:

1. Create the output directory `data/pipeline_runs/` if it does not exist.
2. Write all generated content to a file named `data/pipeline_runs/<slug>_<timestamp>.md` where `<slug>` is the first 40 chars of the concept with spaces replaced by underscores, and `<timestamp>` is `YYYYMMDD_HHMMSS`.
3. The file should contain every generated block in order, with clear headings.

### Phase 6 — Final campaign summary

Print a `## Campaign Summary` section listing:
- Concept used
- Workflow type
- Brand template applied (or "none")
- Steps executed: N succeeded / 0 failed
- Output file path
- Each asset produced with a one-line description

If `--publish` was passed, append a **Publish Checklist** section:

```markdown
## Publish Checklist

- [ ] Shopify Blog: copy `full_content` → Posts > Add blog post
- [ ] Printify: use `generated_image_prompt` to generate mockup → submit to Shopify store
- [ ] YouTube: upload video from `Video Generation Spec`, use thumbnail prompt for thumbnail
- [ ] Twitter: post the Twitter entry from `social_posts`
- [ ] Instagram: post the Instagram entry from `social_posts`
- [ ] Facebook: post the Facebook entry from `social_posts`
- [ ] Email: use `marketing_copy` headline + bullets → Klaviyo / Shopify Email
```

---

## Context keys reference

| Key | Set by | Used by |
|---|---|---|
| `generated_image_prompt` | designer/generate_design | video/generate, writer/video_script |
| `product_description` | writer/product_description | marketer/social_posts, writer/video_script |
| `video_script` | writer/video_script | analyst/summarize |
| `tags` | writer/tags | analyst/summarize |
| `outline` | writer/outline | writer/full_content |
| `full_content` | writer/full_content | analyst/summarize |
| `social_posts` | marketer/social_posts | analyst/summarize |
| `marketing_copy` | marketer/marketing_copy | analyst/summarize |
| `hashtags` | writer/hashtags | analyst/summarize |
| `research` | researcher/research | writer/report, analyst/analyze |
| `report` | writer/report | analyst/summarize |
