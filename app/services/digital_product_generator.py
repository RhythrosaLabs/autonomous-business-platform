"""
AI Digital Product Generator
Creates COMPLETE digital products - full books, courses, coloring books, etc.
Not just cover art, but the entire product with all content.
"""
from app.services.secure_config import get_api_key
from app.tabs.abp_imports_common import (
    os, json, requests, replicate, Path, Optional, Dict, List, Any,
    datetime, logging, BytesIO, base64, time, re, setup_logger
)

logger = setup_logger(__name__)

# Try to import PDF generation libraries
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF generation limited")

# Try to import audio generation
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available - text-to-speech limited")


class AIContentGenerator:
    """Generate text content using AI models."""
    
    def __init__(self):
        self.replicate_token = get_api_key('REPLICATE_API_TOKEN')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self._last_api_call = 0
        self._rate_limit_delay = 12  # seconds between API calls (safe for 6/min limit)
        
    def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limits."""
        elapsed = time.time() - self._last_api_call
        if elapsed < self._rate_limit_delay:
            wait_time = self._rate_limit_delay - elapsed
            logger.info(f"⏳ Rate limit: waiting {wait_time:.1f}s before next API call...")
            time.sleep(wait_time)
        self._last_api_call = time.time()
        
    def generate_text(self, prompt: str, max_tokens: int = 4000, system_prompt: str = None) -> str:
        """
        Generate text content using AI.
        Uses Llama for longer content generation.
        """
        try:
            # Wait for rate limit
            self._wait_for_rate_limit()
            
            # Use Llama 3 70B for text generation
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
            
            logger.info(f"Generating text (max_tokens={max_tokens})...")
            logger.info(f"Prompt preview: {prompt[:200]}...")
            
            output = replicate.run(
                "meta/meta-llama-3-70b-instruct",
                input={
                    "prompt": full_prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
            
            # Collect streaming output
            result = ""
            for item in output:
                result += item
            
            logger.info(f"Generated {len(result)} characters of text")
            if len(result) < 50:
                logger.warning(f"Very short response: {result}")
            
            return result.strip()
            
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"[Content generation failed: {e}]"
    
    def generate_image(self, prompt: str, style: str = "", size: str = "1024x1024") -> Optional[str]:
        """Generate an image using Flux."""
        try:
            # Wait for rate limit
            self._wait_for_rate_limit()
            
            full_prompt = f"{prompt}, {style}" if style else prompt
            
            # Parse size
            width, height = 1024, 1024
            if 'x' in size:
                parts = size.lower().split('x')
                width, height = int(parts[0]), int(parts[1])
            
            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": full_prompt + ", high quality, detailed, professional",
                    "width": width,
                    "height": height,
                    "output_format": "png",
                    "output_quality": 100
                }
            )
            
            # Download and save
            if output:
                image_url = str(output) if not isinstance(output, list) else str(output[0])
                return image_url
                
        except Exception as e:
            logger.error(f"Image generation error: {e}")
        
        return None
    
    def generate_audio_narration(self, text: str, output_path: str, voice: str = "en") -> Optional[str]:
        """
        Generate audio narration from text.
        Uses gTTS for basic TTS, or Replicate for higher quality.
        """
        try:
            # Try Replicate's TTS first for better quality
            try:
                output = replicate.run(
                    "lucataco/xtts-v2",
                    input={
                        "text": text[:500],  # Limit for API
                        "language": "en"
                    }
                )
                if output:
                    # Download audio
                    response = requests.get(str(output))
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        return output_path
            except:
                pass
            
            # Fallback to gTTS
            if GTTS_AVAILABLE:
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(output_path)
                return output_path
                
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
        
        return None


class EBookGenerator:
    """Generate complete e-books with content, images, and audio."""
    
    def __init__(self):
        self.ai = AIContentGenerator()
        self.output_dir = Path("./generated_products/ebooks")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_ebook(
        self,
        topic: str,
        title: str = None,
        num_chapters: int = 5,
        words_per_chapter: int = 1500,
        genre: str = "non-fiction",
        include_images: bool = True,
        include_audio: bool = True,
        target_audience: str = "general",
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate a complete e-book.
        
        Args:
            topic: Main topic/subject of the book
            title: Book title (auto-generated if not provided)
            num_chapters: Number of chapters
            words_per_chapter: Approximate words per chapter
            genre: Book genre (fiction, non-fiction, self-help, etc.)
            include_images: Generate chapter illustrations
            include_audio: Generate audiobook version
            target_audience: Target reader (general, professional, beginner, etc.)
            progress_callback: Function to call with progress updates
            
        Returns:
            Dict with paths to generated files
        """
        result = {
            'title': title,
            'pdf_path': None,
            'epub_path': None,
            'audio_path': None,
            'cover_path': None,
            'images': [],
            'chapters': []
        }
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(message)
        
        update_progress("📝 Generating book outline...")
        
        # Generate title if not provided
        if not title:
            title_prompt = f"""Create a compelling, marketable book title for a {genre} book about: {topic}
            Target audience: {target_audience}
            
            Respond with ONLY the title, nothing else."""
            
            title = self.ai.generate_text(title_prompt, max_tokens=50)
            title = title.strip().strip('"').strip("'")
        
        result['title'] = title
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
        book_dir = self.output_dir / safe_title
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate book outline
        outline_prompt = f"""Create a detailed chapter outline for a {genre} book titled "{title}" about {topic}.
        
Target audience: {target_audience}
Number of chapters: {num_chapters}

For each chapter, provide:
1. Chapter number and title
2. 3-5 key points/sections to cover
3. A brief description (2-3 sentences)

Format as:
CHAPTER 1: [Title]
- Key point 1
- Key point 2
- Key point 3
Description: [Brief description]

Continue for all {num_chapters} chapters."""

        outline = self.ai.generate_text(outline_prompt, max_tokens=2000)
        
        # Parse outline to extract chapter info
        chapters_info = self._parse_outline(outline, num_chapters)
        
        update_progress(f"📖 Generating {num_chapters} chapters...")
        
        # Generate each chapter
        full_text = f"# {title}\n\n"
        chapters_content = []
        
        for i, chapter_info in enumerate(chapters_info):
            update_progress(f"✍️ Writing Chapter {i+1}: {chapter_info['title']}...")
            
            chapter_prompt = f"""Write Chapter {i+1} of the book "{title}".

Chapter Title: {chapter_info['title']}
Key points to cover: {', '.join(chapter_info.get('points', []))}
Chapter description: {chapter_info.get('description', '')}

Genre: {genre}
Target audience: {target_audience}
Approximate length: {words_per_chapter} words

Write engaging, well-structured content. Include:
- An engaging opening
- Clear explanations with examples
- Smooth transitions between sections
- A compelling conclusion that leads to the next chapter

Write the full chapter content now:"""

            chapter_content = self.ai.generate_text(chapter_prompt, max_tokens=3000)
            
            chapters_content.append({
                'number': i + 1,
                'title': chapter_info['title'],
                'content': chapter_content
            })
            
            full_text += f"\n\n## Chapter {i+1}: {chapter_info['title']}\n\n{chapter_content}"
            
            # Generate chapter image if enabled
            if include_images:
                update_progress(f"🎨 Generating illustration for Chapter {i+1}...")
                
                image_prompt = f"""Book illustration for chapter titled "{chapter_info['title']}" 
                from a {genre} book about {topic}. 
                Professional book illustration, detailed, evocative"""
                
                image_url = self.ai.generate_image(image_prompt)
                if image_url:
                    # Download image
                    img_path = book_dir / f"chapter_{i+1}_illustration.png"
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            f.write(response.content)
                        result['images'].append(str(img_path))
                        chapters_content[-1]['image'] = str(img_path)
        
        result['chapters'] = chapters_content
        
        # Generate cover
        update_progress("🎨 Generating book cover...")
        cover_prompt = f"""Professional book cover design for "{title}", 
        a {genre} book about {topic}. 
        Eye-catching, marketable book cover, professional typography space for title,
        bestseller quality design"""
        
        cover_url = self.ai.generate_image(cover_prompt, size="768x1024")
        if cover_url:
            cover_path = book_dir / "cover.png"
            response = requests.get(cover_url)
            if response.status_code == 200:
                with open(cover_path, 'wb') as f:
                    f.write(response.content)
                result['cover_path'] = str(cover_path)
        
        # Generate PDF
        update_progress("📄 Creating PDF...")
        pdf_path = self._create_pdf(book_dir, title, chapters_content, result.get('cover_path'))
        result['pdf_path'] = pdf_path
        
        # Save as text/markdown too
        md_path = book_dir / f"{safe_title}.md"
        with open(md_path, 'w') as f:
            f.write(full_text)
        result['markdown_path'] = str(md_path)
        
        # Generate audiobook if enabled
        if include_audio:
            update_progress("🎙️ Generating audiobook...")
            audio_path = self._create_audiobook(book_dir, title, chapters_content, progress_callback)
            result['audio_path'] = audio_path
        
        update_progress("✅ E-book generation complete!")
        
        return result
    
    def _parse_outline(self, outline: str, num_chapters: int) -> List[Dict]:
        """Parse the generated outline into structured chapter info."""
        chapters = []
        
        # Try to parse chapters from outline
        lines = outline.split('\n')
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for chapter header
            if line.upper().startswith('CHAPTER') or re.match(r'^(Chapter\s*)?\d+[:.)]', line, re.I):
                if current_chapter:
                    chapters.append(current_chapter)
                
                # Extract title
                title_match = re.search(r'[:.]\s*(.+)$', line)
                title = title_match.group(1) if title_match else f"Chapter {len(chapters)+1}"
                
                current_chapter = {
                    'title': title.strip(),
                    'points': [],
                    'description': ''
                }
            elif current_chapter:
                if line.startswith('-') or line.startswith('•'):
                    current_chapter['points'].append(line.lstrip('-•').strip())
                elif line.lower().startswith('description:'):
                    current_chapter['description'] = line.split(':', 1)[1].strip()
                elif not current_chapter['description'] and len(line) > 20:
                    current_chapter['description'] = line
        
        if current_chapter:
            chapters.append(current_chapter)
        
        # Ensure we have enough chapters
        while len(chapters) < num_chapters:
            chapters.append({
                'title': f"Chapter {len(chapters)+1}",
                'points': [],
                'description': ''
            })
        
        return chapters[:num_chapters]
    
    def _create_pdf(self, book_dir: Path, title: str, chapters: List[Dict], cover_path: str = None) -> str:
        """Create a PDF from the book content."""
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, skipping PDF generation")
            return None
        
        pdf_path = book_dir / f"{title.replace(' ', '_')[:30]}.pdf"
        
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'BookTitle',
            parent=styles['Title'],
            fontSize=28,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        chapter_style = ParagraphStyle(
            'ChapterTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceBefore=20,
            spaceAfter=12
        )
        
        body_style = ParagraphStyle(
            'BookBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        story = []
        
        # Cover page
        if cover_path and Path(cover_path).exists():
            try:
                cover_img = Image(cover_path, width=5*inch, height=7*inch)
                story.append(cover_img)
                story.append(PageBreak())
            except:
                pass
        
        # Title page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("Generated by AI", styles['Normal']))
        story.append(PageBreak())
        
        # Table of contents
        story.append(Paragraph("Table of Contents", chapter_style))
        story.append(Spacer(1, 0.3*inch))
        
        for chapter in chapters:
            toc_entry = f"Chapter {chapter['number']}: {chapter['title']}"
            story.append(Paragraph(toc_entry, styles['Normal']))
        
        story.append(PageBreak())
        
        # Chapters
        for chapter in chapters:
            story.append(Paragraph(f"Chapter {chapter['number']}", styles['Heading2']))
            story.append(Paragraph(chapter['title'], chapter_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Chapter image if available
            if chapter.get('image') and Path(chapter['image']).exists():
                try:
                    img = Image(chapter['image'], width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except:
                    pass
            
            # Chapter content - split into paragraphs
            content = chapter['content']
            paragraphs = content.split('\n\n')
            
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Clean up the text for PDF
                    para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    try:
                        story.append(Paragraph(para, body_style))
                    except:
                        # If paragraph fails, try simpler text
                        story.append(Paragraph(para[:500], body_style))
            
            story.append(PageBreak())
        
        # Build PDF
        try:
            doc.build(story)
            return str(pdf_path)
        except Exception as e:
            logger.error(f"PDF creation error: {e}")
            return None
    
    def _create_audiobook(self, book_dir: Path, title: str, chapters: List[Dict], progress_callback=None) -> str:
        """Create an audiobook from the chapters."""
        audio_dir = book_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        
        audio_files = []
        
        for chapter in chapters:
            if progress_callback:
                progress_callback(f"🎙️ Recording Chapter {chapter['number']}...")
            
            audio_path = audio_dir / f"chapter_{chapter['number']}.mp3"
            
            # Prepare text for narration
            narration_text = f"Chapter {chapter['number']}. {chapter['title']}. {chapter['content']}"
            
            # Generate audio (in chunks if needed)
            result = self.ai.generate_audio_narration(
                narration_text[:5000],  # Limit text length
                str(audio_path)
            )
            
            if result:
                audio_files.append(str(audio_path))
        
        # Return path to audio directory
        return str(audio_dir) if audio_files else None


class ColoringBookGenerator:
    """Generate complete printable coloring books."""
    
    def __init__(self):
        self.ai = AIContentGenerator()
        self.output_dir = Path("./generated_products/coloring_books")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_coloring_book(
        self,
        theme: str,
        title: str = None,
        num_pages: int = 20,
        difficulty: str = "adult",  # kids, teen, adult, intricate
        style: str = "mandala",  # mandala, animals, nature, fantasy, geometric, scenes
        include_cover: bool = True,
        page_size: str = "letter",
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate a complete coloring book.
        
        Args:
            theme: Theme of the coloring book
            title: Book title
            num_pages: Number of coloring pages
            difficulty: kids, teen, adult, intricate
            style: mandala, animals, nature, fantasy, geometric, scenes
            include_cover: Generate a cover page
            page_size: letter or a4
            progress_callback: Progress update function
            
        Returns:
            Dict with paths to generated files
        """
        result = {
            'title': title,
            'pdf_path': None,
            'pages': [],
            'cover_path': None
        }
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(message)
        
        # Generate title if not provided
        if not title:
            title = f"{theme.title()} Coloring Book"
        
        result['title'] = title
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip().replace(' ', '_')
        book_dir = self.output_dir / safe_title
        book_dir.mkdir(parents=True, exist_ok=True)
        
        # Difficulty settings
        difficulty_prompts = {
            'kids': "simple outlines, large areas to color, cute and friendly, minimal detail, thick black lines, easy for children",
            'teen': "moderate detail, interesting patterns, medium complexity, clear outlines",
            'adult': "detailed patterns, intricate designs, fine lines, sophisticated composition, relaxing",
            'intricate': "extremely detailed, complex patterns, very fine lines, challenging, meditative, maximum detail"
        }
        
        diff_prompt = difficulty_prompts.get(difficulty, difficulty_prompts['adult'])
        
        # Style settings
        style_prompts = {
            'mandala': "circular mandala pattern, symmetrical, geometric, zen",
            'animals': "animal illustration, wildlife, creature",
            'nature': "nature scene, flowers, plants, trees, botanical",
            'fantasy': "fantasy creature, magical, mythical, enchanted",
            'geometric': "geometric patterns, shapes, abstract, tessellation",
            'scenes': "detailed scene, landscape, setting, environment"
        }
        
        style_prompt = style_prompts.get(style, style_prompts['mandala'])
        
        update_progress(f"🎨 Generating {num_pages} coloring pages...")
        
        # Generate page descriptions for variety
        page_ideas_prompt = f"""Generate {num_pages} unique coloring page ideas for a {difficulty} level coloring book about "{theme}".
        Style: {style}
        
        For each page, provide a brief, specific description (one line each).
        Make each page unique and interesting.
        
        Format: Just list the descriptions, one per line, numbered 1-{num_pages}."""
        
        page_ideas = self.ai.generate_text(page_ideas_prompt, max_tokens=1000)
        ideas = [line.strip() for line in page_ideas.split('\n') if line.strip() and any(c.isalpha() for c in line)]
        ideas = [re.sub(r'^\d+[.):\s]+', '', idea) for idea in ideas]  # Remove numbering
        
        # Ensure we have enough ideas
        while len(ideas) < num_pages:
            ideas.append(f"{theme} {style} design variation {len(ideas)+1}")
        
        # Generate each coloring page
        for i in range(num_pages):
            update_progress(f"✏️ Creating page {i+1}/{num_pages}...")
            
            page_desc = ideas[i] if i < len(ideas) else f"{theme} design {i+1}"
            
            # Generate coloring page image
            image_prompt = f"""Coloring book page, {page_desc}, {theme}, {style_prompt}, {diff_prompt},
            black and white line art, no shading, no gray tones, no color, 
            clean outlines only, white background, printable coloring page,
            professional coloring book illustration"""
            
            image_url = self.ai.generate_image(image_prompt, size="1024x1024")
            
            if image_url:
                page_path = book_dir / f"page_{i+1:02d}.png"
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(page_path, 'wb') as f:
                        f.write(response.content)
                    result['pages'].append(str(page_path))
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Generate cover
        if include_cover:
            update_progress("🎨 Creating cover...")
            
            cover_prompt = f"""Coloring book cover design for "{title}",
            {theme} theme, {style} style, {difficulty} level,
            colorful, inviting, shows sample colored artwork,
            professional book cover, title space at top"""
            
            cover_url = self.ai.generate_image(cover_prompt, size="768x1024")
            if cover_url:
                cover_path = book_dir / "cover.png"
                response = requests.get(cover_url)
                if response.status_code == 200:
                    with open(cover_path, 'wb') as f:
                        f.write(response.content)
                    result['cover_path'] = str(cover_path)
        
        # Create PDF
        update_progress("📄 Compiling PDF...")
        pdf_path = self._create_coloring_pdf(book_dir, title, result['pages'], result.get('cover_path'), page_size)
        result['pdf_path'] = pdf_path
        
        update_progress("✅ Coloring book complete!")
        
        return result
    
    def _create_coloring_pdf(self, book_dir: Path, title: str, pages: List[str], cover_path: str, page_size: str) -> str:
        """Create a PDF coloring book."""
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available")
            return None
        
        pdf_path = book_dir / f"{title.replace(' ', '_')[:30]}.pdf"
        
        size = letter if page_size == 'letter' else A4
        doc = SimpleDocTemplate(str(pdf_path), pagesize=size, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        
        story = []
        
        # Cover
        if cover_path and Path(cover_path).exists():
            try:
                img = Image(cover_path, width=7*inch, height=9*inch)
                story.append(img)
                story.append(PageBreak())
            except:
                pass
        
        # Coloring pages
        for page_path in pages:
            if Path(page_path).exists():
                try:
                    img = Image(page_path, width=7.5*inch, height=9.5*inch)
                    story.append(img)
                    story.append(PageBreak())
                except:
                    pass
        
        try:
            doc.build(story)
            return str(pdf_path)
        except Exception as e:
            logger.error(f"PDF error: {e}")
            return None


class CourseGenerator:
    """Generate complete online courses with lessons, slides, and materials."""
    
    def __init__(self):
        self.ai = AIContentGenerator()
        self.output_dir = Path("./generated_products/courses")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_course(
        self,
        topic: str,
        title: str = None,
        num_modules: int = 5,
        lessons_per_module: int = 3,
        include_slides: bool = True,
        include_worksheets: bool = True,
        include_quizzes: bool = True,
        include_audio: bool = True,
        skill_level: str = "beginner",  # beginner, intermediate, advanced
        target_audience: str = "general",
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate a complete online course.
        
        Args:
            topic: Course topic
            title: Course title
            num_modules: Number of modules
            lessons_per_module: Lessons per module
            include_slides: Generate slide decks
            include_worksheets: Generate worksheets/exercises
            include_quizzes: Generate quizzes
            include_audio: Generate audio narration
            skill_level: beginner, intermediate, advanced
            target_audience: Who the course is for
            progress_callback: Progress function
            
        Returns:
            Dict with all course materials
        """
        result = {
            'title': title,
            'modules': [],
            'slides_dir': None,
            'worksheets_dir': None,
            'audio_dir': None,
            'pdf_path': None
        }
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(message)
        
        # Generate title if not provided
        if not title:
            title_prompt = f"Create a compelling online course title for a {skill_level} level course about: {topic}. Response with only the title."
            title = self.ai.generate_text(title_prompt, max_tokens=50).strip().strip('"')
        
        result['title'] = title
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip().replace(' ', '_')
        course_dir = self.output_dir / safe_title
        course_dir.mkdir(parents=True, exist_ok=True)
        
        update_progress("📋 Creating course curriculum...")
        
        # Generate course structure
        curriculum_prompt = f"""Create a detailed curriculum for an online course:

Title: {title}
Topic: {topic}
Skill Level: {skill_level}
Target Audience: {target_audience}
Number of Modules: {num_modules}
Lessons per Module: {lessons_per_module}

For each module, provide:
- Module title
- Module description (2-3 sentences)
- List of {lessons_per_module} lesson titles

Format:
MODULE 1: [Title]
Description: [Description]
Lessons:
- Lesson 1: [Title]
- Lesson 2: [Title]
- Lesson 3: [Title]

Continue for all {num_modules} modules."""

        curriculum = self.ai.generate_text(curriculum_prompt, max_tokens=2000)
        modules_info = self._parse_curriculum(curriculum, num_modules, lessons_per_module)
        
        # Create subdirectories
        if include_slides:
            slides_dir = course_dir / "slides"
            slides_dir.mkdir(exist_ok=True)
            result['slides_dir'] = str(slides_dir)
        
        if include_worksheets:
            worksheets_dir = course_dir / "worksheets"
            worksheets_dir.mkdir(exist_ok=True)
            result['worksheets_dir'] = str(worksheets_dir)
        
        if include_audio:
            audio_dir = course_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            result['audio_dir'] = str(audio_dir)
        
        # Generate each module
        total_lessons = num_modules * lessons_per_module
        current_lesson = 0
        
        for m_idx, module_info in enumerate(modules_info):
            update_progress(f"📚 Creating Module {m_idx+1}: {module_info['title']}...")
            
            module_data = {
                'number': m_idx + 1,
                'title': module_info['title'],
                'description': module_info.get('description', ''),
                'lessons': []
            }
            
            for l_idx, lesson_title in enumerate(module_info.get('lessons', [])):
                current_lesson += 1
                update_progress(f"✍️ Writing Lesson {current_lesson}/{total_lessons}: {lesson_title}...")
                
                # Generate lesson content
                lesson_prompt = f"""Write a detailed lesson for an online course.

Course: {title}
Module {m_idx+1}: {module_info['title']}
Lesson {l_idx+1}: {lesson_title}
Skill Level: {skill_level}

Include:
1. Learning Objectives (3-5 bullet points)
2. Introduction
3. Main Content (detailed explanation with examples)
4. Key Takeaways
5. Practice Exercise

Write comprehensive, educational content that's engaging and easy to follow."""

                lesson_content = self.ai.generate_text(lesson_prompt, max_tokens=2500)
                
                lesson_data = {
                    'number': l_idx + 1,
                    'title': lesson_title,
                    'content': lesson_content
                }
                
                # Generate slide deck for lesson
                if include_slides:
                    update_progress(f"📊 Creating slides for Lesson {current_lesson}...")
                    slides_content = self._generate_slides(
                        module_info['title'],
                        lesson_title,
                        lesson_content,
                        slides_dir,
                        m_idx + 1,
                        l_idx + 1
                    )
                    lesson_data['slides'] = slides_content
                
                # Generate audio narration
                if include_audio:
                    update_progress(f"🎙️ Recording audio for Lesson {current_lesson}...")
                    audio_path = audio_dir / f"module{m_idx+1}_lesson{l_idx+1}.mp3"
                    narration = f"Module {m_idx+1}, Lesson {l_idx+1}: {lesson_title}. {lesson_content[:3000]}"
                    self.ai.generate_audio_narration(narration, str(audio_path))
                    lesson_data['audio'] = str(audio_path)
                
                module_data['lessons'].append(lesson_data)
            
            # Generate module quiz
            if include_quizzes:
                update_progress(f"❓ Creating quiz for Module {m_idx+1}...")
                quiz = self._generate_quiz(module_info, module_data['lessons'])
                module_data['quiz'] = quiz
            
            # Generate module worksheet
            if include_worksheets:
                update_progress(f"📝 Creating worksheet for Module {m_idx+1}...")
                worksheet = self._generate_worksheet(
                    module_info,
                    module_data['lessons'],
                    worksheets_dir,
                    m_idx + 1
                )
                module_data['worksheet'] = worksheet
            
            result['modules'].append(module_data)
        
        # Generate course PDF
        update_progress("📄 Compiling course PDF...")
        pdf_path = self._create_course_pdf(course_dir, title, result['modules'])
        result['pdf_path'] = pdf_path
        
        # Save course structure as JSON
        json_path = course_dir / "course_structure.json"
        with open(json_path, 'w') as f:
            # Create a serializable version
            json_data = {
                'title': result['title'],
                'modules': [{
                    'number': m['number'],
                    'title': m['title'],
                    'description': m.get('description', ''),
                    'lessons': [{
                        'number': l['number'],
                        'title': l['title']
                    } for l in m['lessons']]
                } for m in result['modules']]
            }
            json.dump(json_data, f, indent=2)
        
        result['structure_json'] = str(json_path)
        
        update_progress("✅ Course generation complete!")
        
        return result
    
    def _parse_curriculum(self, curriculum: str, num_modules: int, lessons_per_module: int) -> List[Dict]:
        """Parse curriculum text into structured modules."""
        modules = []
        current_module = None
        
        logger.info(f"Raw curriculum to parse:\n{curriculum}")
        
        for line in curriculum.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Match MODULE headers - various formats
            # MODULE 1: Title, Module 1 - Title, **Module 1: Title**, etc.
            module_match = re.match(r'^\*{0,2}(?:MODULE|Module)\s*(\d+)[:\s\-–]+\s*(.+?)\*{0,2}$', line)
            if not module_match:
                module_match = re.match(r'^(\d+)\.\s*(?:MODULE|Module)?[:\s\-–]*\s*(.+)$', line, re.I)
            
            if module_match or line.upper().startswith('MODULE'):
                if current_module and current_module.get('title'):
                    modules.append(current_module)
                
                if module_match:
                    title = module_match.group(2).strip().strip('*').strip()
                else:
                    # Fallback parsing
                    title_match = re.search(r'[:\-–]\s*(.+)$', line)
                    title = title_match.group(1).strip() if title_match else line
                
                current_module = {
                    'title': title or f"Module {len(modules)+1}",
                    'description': '',
                    'lessons': []
                }
                logger.info(f"Parsed module: {current_module['title']}")
                
            elif current_module:
                # Match lesson lines
                if line.lower().startswith('description:'):
                    current_module['description'] = line.split(':', 1)[1].strip()
                elif line.startswith(('-', '•', '*', '–')) or re.match(r'^\d+\.', line):
                    # Remove bullet/number and "Lesson X:" prefix
                    lesson = re.sub(r'^[-•*–]\s*', '', line)
                    lesson = re.sub(r'^\d+\.\s*', '', lesson)
                    lesson = re.sub(r'^Lesson\s*\d+[:\s\-–]*', '', lesson, flags=re.I)
                    lesson = lesson.strip().strip('*').strip()
                    
                    if lesson and len(lesson) > 3:
                        current_module['lessons'].append(lesson)
                        logger.info(f"  Parsed lesson: {lesson}")
                        
                elif re.match(r'^Lesson\s*\d+', line, re.I):
                    # Direct "Lesson X: Title" format
                    lesson = re.sub(r'^Lesson\s*\d+[:\s\-–]*', '', line, flags=re.I)
                    lesson = lesson.strip()
                    if lesson:
                        current_module['lessons'].append(lesson)
                        logger.info(f"  Parsed lesson: {lesson}")
        
        if current_module and current_module.get('title'):
            modules.append(current_module)
        
        logger.info(f"Total modules parsed: {len(modules)}")
        
        # If parsing failed completely, generate default structure
        if len(modules) == 0:
            logger.warning("Curriculum parsing failed, generating default structure")
            for i in range(num_modules):
                modules.append({
                    'title': f"Module {i+1}: Core Concepts",
                    'description': '',
                    'lessons': [f"Key Topic {j+1}" for j in range(lessons_per_module)]
                })
        
        # Ensure correct number of modules
        while len(modules) < num_modules:
            modules.append({
                'title': f"Advanced Topics {len(modules)+1}",
                'description': '',
                'lessons': [f"Extended Learning {i+1}" for i in range(lessons_per_module)]
            })
        
        # Ensure each module has enough lessons
        for module in modules:
            while len(module['lessons']) < lessons_per_module:
                module['lessons'].append(f"Additional Concept {len(module['lessons'])+1}")
            # Trim excess
            module['lessons'] = module['lessons'][:lessons_per_module]
        
        return modules[:num_modules]
    
    def _generate_slides(self, module_title: str, lesson_title: str, content: str, 
                         slides_dir: Path, module_num: int, lesson_num: int) -> Dict:
        """Generate slide content for a lesson."""
        slides_prompt = f"""Create a slide deck outline for this lesson:
Module: {module_title}
Lesson: {lesson_title}

Content summary: {content[:1500]}

Create 8-10 slides with:
- Slide title
- 3-5 bullet points per slide

Format:
SLIDE 1: [Title]
• Point 1
• Point 2
• Point 3

Continue for all slides."""

        slides_text = self.ai.generate_text(slides_prompt, max_tokens=1500)
        
        # Save slides as markdown
        slides_path = slides_dir / f"module{module_num}_lesson{lesson_num}_slides.md"
        with open(slides_path, 'w') as f:
            f.write(f"# {lesson_title}\n\n")
            f.write(slides_text)
        
        return {'markdown_path': str(slides_path), 'content': slides_text}
    
    def _generate_quiz(self, module_info: Dict, lessons: List[Dict]) -> Dict:
        """Generate a quiz for the module."""
        lessons_summary = "\n".join([f"- {l['title']}" for l in lessons])
        
        quiz_prompt = f"""Create a 10-question quiz for this module:
Module: {module_info['title']}
Lessons covered:
{lessons_summary}

Create a mix of:
- Multiple choice questions (5)
- True/False questions (3)
- Short answer questions (2)

Format:
Q1 (Multiple Choice): [Question]
A) [Option]
B) [Option]
C) [Option]
D) [Option]
Answer: [Letter]

Continue for all 10 questions."""

        quiz_text = self.ai.generate_text(quiz_prompt, max_tokens=1500)
        
        return {'content': quiz_text}
    
    def _generate_worksheet(self, module_info: Dict, lessons: List[Dict], 
                           worksheets_dir: Path, module_num: int) -> str:
        """Generate a worksheet for the module."""
        # Build lesson summaries from actual content
        lessons_summary = ""
        for l in lessons:
            content_preview = l.get('content', '')[:300] if l.get('content') else 'Lesson content'
            lessons_summary += f"- {l['title']}: {content_preview}...\n"
        
        worksheet_prompt = f"""Create a practical worksheet for this module:
Module: {module_info['title']}

Lessons covered:
{lessons_summary}

Include:
1. Key Concepts Review (5 fill-in-the-blank questions)
2. Practical Exercises (3-5 hands-on activities)  
3. Reflection Questions (3 thought-provoking questions)
4. Action Items / Next Steps (5 actionable items)

Make it engaging, actionable, and directly related to the lesson content.
Write the complete worksheet content now:"""

        worksheet_text = self.ai.generate_text(worksheet_prompt, max_tokens=1500)
        
        logger.info(f"Generated worksheet content ({len(worksheet_text)} chars)")
        
        worksheet_path = worksheets_dir / f"module{module_num}_worksheet.md"
        with open(worksheet_path, 'w') as f:
            f.write(f"# {module_info['title']} - Worksheet\n\n")
            f.write(worksheet_text if worksheet_text else "Worksheet content generation failed.")
        
        return str(worksheet_path)
    
    def _create_course_pdf(self, course_dir: Path, title: str, modules: List[Dict]) -> str:
        """Create a comprehensive course PDF."""
        if not REPORTLAB_AVAILABLE:
            return None
        
        pdf_path = course_dir / f"{title.replace(' ', '_')[:30]}_complete.pdf"
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        
        story = []
        
        # Title page
        title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=28, spaceAfter=30, alignment=TA_CENTER)
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, inch))
        story.append(Paragraph("Complete Course Materials", styles['Heading2']))
        story.append(PageBreak())
        
        # Table of contents
        story.append(Paragraph("Course Contents", styles['Heading1']))
        story.append(Spacer(1, 0.3*inch))
        
        for module in modules:
            story.append(Paragraph(f"Module {module['number']}: {module['title']}", styles['Heading3']))
            for lesson in module['lessons']:
                story.append(Paragraph(f"  • Lesson {lesson['number']}: {lesson['title']}", styles['Normal']))
        
        story.append(PageBreak())
        
        # Module content
        for module in modules:
            story.append(Paragraph(f"Module {module['number']}: {module['title']}", styles['Heading1']))
            if module.get('description'):
                story.append(Paragraph(module['description'], styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            for lesson in module['lessons']:
                story.append(Paragraph(f"Lesson {lesson['number']}: {lesson['title']}", styles['Heading2']))
                
                # Clean and add content
                content = lesson['content']
                for para in content.split('\n\n'):
                    para = para.strip()
                    if para:
                        para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        try:
                            story.append(Paragraph(para, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        except:
                            pass
                
                story.append(PageBreak())
        
        try:
            doc.build(story)
            return str(pdf_path)
        except Exception as e:
            logger.error(f"Course PDF error: {e}")
            return None


class ComicBookGenerator:
    """Generate complete comic books and graphic novels."""
    
    def __init__(self):
        self.ai = AIContentGenerator()
        self.output_dir = Path("./generated_products/comics")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comic(
        self,
        story_concept: str,
        title: str = None,
        num_pages: int = 10,
        style: str = "american superhero",
        genre: str = "action",
        include_cover: bool = True,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Generate a complete comic book."""
        result = {
            'title': title,
            'pages': [],
            'cover_path': None,
            'pdf_path': None,
            'script': None
        }
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(message)
        
        # Generate title
        if not title:
            title_prompt = f"Create an exciting comic book title for: {story_concept}. Genre: {genre}. Response with only the title."
            title = self.ai.generate_text(title_prompt, max_tokens=30).strip().strip('"')
        
        result['title'] = title
        safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip().replace(' ', '_')
        comic_dir = self.output_dir / safe_title
        comic_dir.mkdir(parents=True, exist_ok=True)
        
        update_progress("📝 Writing comic script...")
        
        # Generate full script
        script_prompt = f"""Write a complete comic book script for "{title}".

Story concept: {story_concept}
Genre: {genre}
Style: {style}
Number of pages: {num_pages}

For each page, provide:
- Page number
- Panel descriptions (3-5 panels per page)
- Dialogue/captions for each panel
- Action descriptions

Format:
PAGE 1
Panel 1: [Visual description]
Caption: [Narration text if any]
Character: "Dialogue"

Panel 2: [Visual description]
...

Continue for all {num_pages} pages. Make it engaging with good pacing."""

        script = self.ai.generate_text(script_prompt, max_tokens=4000)
        result['script'] = script
        
        # Save script
        script_path = comic_dir / "script.txt"
        with open(script_path, 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(script)
        
        # Parse script for page descriptions
        pages_info = self._parse_comic_script(script, num_pages)
        
        # Generate comic pages
        for i, page_info in enumerate(pages_info):
            update_progress(f"🎨 Drawing page {i+1}/{num_pages}...")
            
            page_prompt = f"""Comic book page, {style} style, {genre} genre,
            {page_info['description']},
            dynamic panel layout, professional comic art,
            bold inks, dramatic lighting, sequential art"""
            
            image_url = self.ai.generate_image(page_prompt, size="768x1024")
            
            if image_url:
                page_path = comic_dir / f"page_{i+1:02d}.png"
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(page_path, 'wb') as f:
                        f.write(response.content)
                    result['pages'].append(str(page_path))
            
            time.sleep(0.5)
        
        # Generate cover
        if include_cover:
            update_progress("🎨 Creating cover...")
            
            cover_prompt = f"""Comic book cover for "{title}",
            {style} style, {genre} genre,
            {story_concept},
            dynamic action pose, title space at top,
            professional comic book cover art, eye-catching"""
            
            cover_url = self.ai.generate_image(cover_prompt, size="768x1024")
            if cover_url:
                cover_path = comic_dir / "cover.png"
                response = requests.get(cover_url)
                if response.status_code == 200:
                    with open(cover_path, 'wb') as f:
                        f.write(response.content)
                    result['cover_path'] = str(cover_path)
        
        # Create PDF
        update_progress("📄 Compiling PDF...")
        pdf_path = self._create_comic_pdf(comic_dir, title, result['pages'], result.get('cover_path'))
        result['pdf_path'] = pdf_path
        
        update_progress("✅ Comic book complete!")
        
        return result
    
    def _parse_comic_script(self, script: str, num_pages: int) -> List[Dict]:
        """Parse comic script into page descriptions."""
        pages = []
        current_page = None
        
        for line in script.split('\n'):
            line = line.strip()
            if re.match(r'^PAGE\s*\d+', line, re.I):
                if current_page:
                    pages.append(current_page)
                current_page = {'description': '', 'panels': []}
            elif current_page:
                if line.startswith('Panel') or line.startswith('PANEL'):
                    current_page['panels'].append(line)
                    current_page['description'] += ' ' + line
                elif line:
                    current_page['description'] += ' ' + line
        
        if current_page:
            pages.append(current_page)
        
        # Ensure we have enough pages
        while len(pages) < num_pages:
            pages.append({'description': f'Action scene page {len(pages)+1}'})
        
        return pages[:num_pages]
    
    def _create_comic_pdf(self, comic_dir: Path, title: str, pages: List[str], cover_path: str) -> str:
        """Create comic book PDF."""
        if not REPORTLAB_AVAILABLE:
            return None
        
        pdf_path = comic_dir / f"{title.replace(' ', '_')[:30]}.pdf"
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
        story = []
        
        # Cover
        if cover_path and Path(cover_path).exists():
            try:
                img = Image(cover_path, width=7.5*inch, height=10*inch)
                story.append(img)
                story.append(PageBreak())
            except:
                pass
        
        # Pages
        for page_path in pages:
            if Path(page_path).exists():
                try:
                    img = Image(page_path, width=7.5*inch, height=10*inch)
                    story.append(img)
                    story.append(PageBreak())
                except:
                    pass
        
        try:
            doc.build(story)
            return str(pdf_path)
        except Exception as e:
            logger.error(f"Comic PDF error: {e}")
            return None


class AudioProductGenerator:
    """Generate audio product metadata and promotional materials."""
    
    def __init__(self):
        self.ai = AIContentGenerator()
        self.output_dir = Path("./generated_products/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_sample_pack_listing(
        self,
        pack_name: str,
        genre: str,
        description: str,
        num_samples: int = 50,
        include_cover: bool = True,
        include_demo: bool = False,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate complete sample pack listing materials.
        Creates cover art, description, track list, and promotional materials.
        """
        result = {
            'name': pack_name,
            'cover_path': None,
            'description': None,
            'track_list': None,
            'promo_images': []
        }
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(message)
        
        safe_name = re.sub(r'[^\w\s-]', '', pack_name)[:40].strip().replace(' ', '_')
        pack_dir = self.output_dir / safe_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        
        update_progress("📝 Generating sample pack details...")
        
        # Generate detailed description
        desc_prompt = f"""Write a compelling product description for a sample pack:

Name: {pack_name}
Genre: {genre}
Description: {description}
Number of samples: {num_samples}

Include:
1. Hook/headline
2. What's included
3. Key features
4. Who it's for
5. Technical specs (formats, BPM range, key info)

Make it exciting and professional for music producers."""

        full_description = self.ai.generate_text(desc_prompt, max_tokens=1000)
        result['description'] = full_description
        
        # Save description
        desc_path = pack_dir / "description.txt"
        with open(desc_path, 'w') as f:
            f.write(full_description)
        
        # Generate track list
        update_progress("📋 Generating track list...")
        
        track_prompt = f"""Generate a list of {num_samples} sample names for a {genre} sample pack called "{pack_name}".

Include a mix of:
- One shots (kicks, snares, hats, etc.)
- Loops (melodic, drum, bass)
- FX and transitions

Format as a simple list with categories:

=== DRUMS ===
Kick_01.wav
...

=== MELODICS ===
...

Make the names creative and genre-appropriate."""

        track_list = self.ai.generate_text(track_prompt, max_tokens=1500)
        result['track_list'] = track_list
        
        track_path = pack_dir / "track_list.txt"
        with open(track_path, 'w') as f:
            f.write(track_list)
        
        # Generate cover art
        if include_cover:
            update_progress("🎨 Creating cover art...")
            
            cover_prompt = f"""Sample pack cover art for "{pack_name}",
            {genre} music production,
            dark professional aesthetic,
            abstract waveforms and audio visualization,
            modern, sleek design,
            space for title text"""
            
            cover_url = self.ai.generate_image(cover_prompt, size="1024x1024")
            if cover_url:
                cover_path = pack_dir / "cover.png"
                response = requests.get(cover_url)
                if response.status_code == 200:
                    with open(cover_path, 'wb') as f:
                        f.write(response.content)
                    result['cover_path'] = str(cover_path)
        
        # Generate promotional images
        update_progress("📸 Creating promo images...")
        
        promo_styles = ['instagram square', 'banner wide', 'story vertical']
        sizes = ['1080x1080', '1200x628', '1080x1920']
        
        for style, size in zip(promo_styles[:2], sizes[:2]):  # Just 2 promos
            promo_prompt = f"""Promotional image for "{pack_name}" sample pack,
            {genre} music production,
            {style} format,
            featuring the product,
            bold text space,
            professional advertising design"""
            
            promo_url = self.ai.generate_image(promo_prompt, size=size)
            if promo_url:
                promo_path = pack_dir / f"promo_{style.replace(' ', '_')}.png"
                response = requests.get(promo_url)
                if response.status_code == 200:
                    with open(promo_path, 'wb') as f:
                        f.write(response.content)
                    result['promo_images'].append(str(promo_path))
        
        update_progress("✅ Sample pack materials complete!")
        
        return result


# Convenience function for the pages
def generate_complete_product(
    product_type: str,
    progress_callback=None,
    **kwargs
) -> Dict[str, Any]:
    """
    Main entry point for generating complete digital products.
    
    Args:
        product_type: Type of product to generate
        progress_callback: Function to call with progress updates
        **kwargs: Product-specific parameters
        
    Returns:
        Dict with all generated files and content
    """
    generators = {
        'ebook': EBookGenerator,
        'coloring_book': ColoringBookGenerator,
        'course': CourseGenerator,
        'comic_book': ComicBookGenerator,
        'graphic_novel': ComicBookGenerator,
        'sample_pack': AudioProductGenerator,
        'drum_kit': AudioProductGenerator,
        'music_loops': AudioProductGenerator,
        'sound_design': AudioProductGenerator
    }
    
    generator_class = generators.get(product_type)
    
    if not generator_class:
        logger.error(f"Unknown product type: {product_type}")
        return None
    
    generator = generator_class()
    
    # Route to appropriate method
    if product_type == 'ebook':
        return generator.generate_ebook(progress_callback=progress_callback, **kwargs)
    elif product_type == 'coloring_book':
        return generator.generate_coloring_book(progress_callback=progress_callback, **kwargs)
    elif product_type == 'course':
        return generator.generate_course(progress_callback=progress_callback, **kwargs)
    elif product_type in ['comic_book', 'graphic_novel']:
        return generator.generate_comic(progress_callback=progress_callback, **kwargs)
    elif product_type in ['sample_pack', 'drum_kit', 'music_loops', 'sound_design']:
        return generator.generate_sample_pack_listing(progress_callback=progress_callback, **kwargs)
    
    return None


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Digital Product Generator initialized")
    print(f"ReportLab available: {REPORTLAB_AVAILABLE}")
    print(f"gTTS available: {GTTS_AVAILABLE}")
