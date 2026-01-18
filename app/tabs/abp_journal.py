from abp_imports_common import (
    st, datetime, timedelta, uuid, json, logging, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.services.platform_integrations import tracked_replicate_run

try:
    from app.services.platform_helpers import _get_replicate_token
except ImportError:
    def _get_replicate_token() -> str:
        return ""

try:
    from performance_optimizations import get_replicate_client
    PERF_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    PERF_OPTIMIZATIONS_AVAILABLE = False
    def get_replicate_client(api_token: str = None):
        """Fallback if performance_optimizations not available"""
        if api_token:
            import replicate
            return replicate.Client(api_token=api_token)
        token = _get_replicate_token()
        if token:
            import replicate
            return replicate.Client(api_token=token)
        return None

def render_journal_tab():
    """
    Renders the Journal & Notes tab (Tab 11).
    """
    st.markdown('<div class="main-header">📓 AI-Powered Journal & Notes</div>', unsafe_allow_html=True)
    
    # Custom CSS for journal
    st.markdown("""
    <style>
    .journal-entry {
        background: linear-gradient(135deg, #667eea15, #764ba215);
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    .idea-card {
        background: linear-gradient(135deg, #f093fb15, #f5576c15);
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #f093fb;
    }
    .ai-suggestion {
        background: linear-gradient(135deg, #4facfe15, #00f2fe15);
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        border: 1px dashed #4facfe;
    }
    .mood-indicator {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    note_tabs = st.tabs(["📝 Smart Notes", "💡 Idea Lab", "📅 Daily Journal", "🎯 Goals & Tasks", "🔍 Search & Insights"])
    
    # Initialize all journal storage
    if 'saved_notes' not in st.session_state:
        st.session_state.saved_notes = []
    if 'saved_ideas' not in st.session_state:
        st.session_state.saved_ideas = []
    if 'journal_entries' not in st.session_state:
        st.session_state.journal_entries = []
    if 'journal_goals' not in st.session_state:
        st.session_state.journal_goals = []
    
    # ========== TAB 1: SMART NOTES ==========
    with note_tabs[0]:
        st.markdown("### 📝 Smart Notes with AI")
        st.caption("Write notes and let AI help organize, summarize, and enhance them")
        
        col_note_input, col_note_ai = st.columns([2, 1])
        
        with col_note_input:
            note_title = st.text_input("Note Title (optional)", placeholder="Meeting notes, Research, Ideas...", key="note_title_input")
            note_text = st.text_area("Your Note", height=200, placeholder="Start writing your thoughts...\n\nTip: Write naturally - AI will help organize!", key="smart_note_area")
            
            note_tags = st.multiselect(
                "Tags",
                ["📊 Business", "🎨 Creative", "💻 Technical", "📈 Marketing", "🛒 Product", "📚 Research", "💭 Personal", "⚡ Urgent"],
                key="note_tags"
            )
            
            col_save, col_ai_enhance = st.columns(2)
            with col_save:
                if st.button("💾 Save Note", use_container_width=True, type="primary"):
                    if note_text.strip():
                        new_note = {
                            'id': str(uuid.uuid4())[:8],
                            'title': note_title or f"Note {len(st.session_state.saved_notes) + 1}",
                            'text': note_text,
                            'tags': note_tags,
                            'created_at': dt.now().isoformat(),
                            'ai_summary': None,
                            'ai_actions': []
                        }
                        st.session_state.saved_notes.insert(0, new_note)
                        st.success("✅ Note saved!")
                        st.rerun()
                    else:
                        st.warning("Please enter a note first")
            
            with col_ai_enhance:
                if st.button("✨ AI Enhance & Save", use_container_width=True):
                    replicate_token = _get_replicate_token()
                    replicate_client = get_replicate_client()
                    if note_text.strip() and replicate_token and replicate_client:
                        with st.spinner("🤖 AI is analyzing your note..."):
                            try:
                                # Use Claude to enhance the note
                                enhance_prompt = f"""Analyze this note and provide:
1. A concise summary (2-3 sentences)
2. Key action items (if any)
3. Suggested tags/categories
4. Related topics to explore

Note: {note_text}

Respond in JSON format:
{{"summary": "...", "actions": ["action1", "action2"], "suggested_tags": ["tag1", "tag2"], "related_topics": ["topic1", "topic2"]}}"""
                                
                                response = tracked_replicate_run(
                                    replicate_client,
                                    "meta/meta-llama-3-70b-instruct",
                                    {"prompt": enhance_prompt, "max_tokens": 500},
                                    operation_name="Note Enhancement"
                                )
                                ai_response = "".join(response) if isinstance(response, list) else response
                                
                                # Try to parse JSON
                                try:
                                    import re
                                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                                    if json_match:
                                        ai_data = json.loads(json_match.group())
                                    else:
                                        ai_data = {"summary": ai_response[:200], "actions": [], "suggested_tags": [], "related_topics": []}
                                except:
                                    ai_data = {"summary": ai_response[:200], "actions": [], "suggested_tags": [], "related_topics": []}
                                
                                new_note = {
                                    'id': str(uuid.uuid4())[:8],
                                    'title': note_title or f"Note {len(st.session_state.saved_notes) + 1}",
                                    'text': note_text,
                                    'tags': note_tags + ai_data.get('suggested_tags', [])[:3],
                                    'created_at': dt.now().isoformat(),
                                    'ai_summary': ai_data.get('summary'),
                                    'ai_actions': ai_data.get('actions', []),
                                    'ai_related': ai_data.get('related_topics', [])
                                }
                                st.session_state.saved_notes.insert(0, new_note)
                                st.success("✅ Note enhanced and saved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"AI enhancement failed: {e}")
                    else:
                        st.warning("Enter a note and ensure API is configured")
        
        with col_note_ai:
            st.markdown("#### 🤖 AI Assistant")
            
            ai_action = st.selectbox("Quick AI Action", [
                "📋 Summarize my notes",
                "🎯 Extract action items",
                "🔗 Find connections",
                "📊 Analyze patterns",
                "✍️ Improve writing"
            ], key="note_ai_action")
            
            if st.button("🚀 Run AI Action", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if note_text.strip() and replicate_token and replicate_client:
                    with st.spinner("Processing..."):
                        try:
                            action_prompts = {
                                "📋 Summarize my notes": f"Summarize this concisely in 2-3 bullet points:\n{note_text}",
                                "🎯 Extract action items": f"Extract all actionable tasks from this note as a numbered list:\n{note_text}",
                                "🔗 Find connections": f"What business/creative connections or opportunities does this note suggest?\n{note_text}",
                                "📊 Analyze patterns": f"What patterns, themes or insights can you identify in this note?\n{note_text}",
                                "✍️ Improve writing": f"Rewrite this note to be clearer and more professional while keeping the meaning:\n{note_text}"
                            }
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": action_prompts[ai_action], "max_tokens": 500},
                                operation_name="Note AI Action"
                            )
                            result = "".join(response) if isinstance(response, list) else response
                            st.markdown("**AI Result:**")
                            st.markdown(f'<div class="ai-suggestion">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("Enter a note to analyze")
            
            st.markdown("---")
            st.markdown("#### 📊 Note Stats")
            st.metric("Total Notes", len(st.session_state.saved_notes))
            if st.session_state.saved_notes:
                recent_count = sum(1 for n in st.session_state.saved_notes 
                                   if (dt.now() - dt.fromisoformat(n['created_at'])).days < 7)
                st.metric("This Week", recent_count)
        
        # Display saved notes
        st.markdown("---")
        st.markdown("### 📚 Your Notes")
        
        # Search and filter
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            note_search = st.text_input("🔍 Search notes...", key="note_search", placeholder="Search by title or content...")
        with col_filter:
            sort_by = st.selectbox("Sort by", ["Newest", "Oldest", "With AI Summary"], key="note_sort")
        
        filtered_notes = st.session_state.saved_notes
        if note_search:
            filtered_notes = [n for n in filtered_notes if 
                            note_search.lower() in n.get('title', '').lower() or 
                            note_search.lower() in n.get('text', '').lower()]
        
        if sort_by == "Oldest":
            filtered_notes = list(reversed(filtered_notes))
        elif sort_by == "With AI Summary":
            filtered_notes = [n for n in filtered_notes if n.get('ai_summary')]
        
        if filtered_notes:
            for idx, note in enumerate(filtered_notes[:15]):
                with st.expander(f"📝 {note.get('title', 'Untitled')} - {note['created_at'][:16].replace('T', ' ')}"):
                    # Tags
                    if note.get('tags'):
                        st.markdown(" ".join([f"`{tag}`" for tag in note['tags']]))
                    
                    # Content
                    st.markdown(note['text'])
                    
                    # AI Summary
                    if note.get('ai_summary'):
                        st.markdown("---")
                        st.markdown("**🤖 AI Summary:**")
                        st.info(note['ai_summary'])
                    
                    # AI Actions
                    if note.get('ai_actions'):
                        st.markdown("**🎯 Action Items:**")
                        for action in note['ai_actions']:
                            st.checkbox(action, key=f"action_{note['id']}_{action[:20]}")
                    
                    # Controls
                    col_edit, col_del = st.columns(2)
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_note_{note['id']}"):
                            st.session_state.saved_notes = [n for n in st.session_state.saved_notes if n['id'] != note['id']]
                            st.rerun()
        else:
            st.info("No notes found. Start writing above!")
    
    # ========== TAB 2: IDEA LAB ==========
    with note_tabs[1]:
        st.markdown("### 💡 AI-Powered Idea Lab")
        st.caption("Capture ideas and let AI help develop, connect, and expand them")
        
        col_idea_input, col_idea_develop = st.columns([3, 2])
        
        with col_idea_input:
            idea_text = st.text_area("Your Idea", height=150, placeholder="Describe your idea... What problem does it solve? Who is it for?", key="idea_lab_text")
            
            col_cat, col_priority = st.columns(2)
            with col_cat:
                idea_category = st.selectbox("Category", [
                    "🛍️ Product Idea",
                    "📢 Marketing Campaign", 
                    "🎨 Design Concept",
                    "📝 Content Idea",
                    "💼 Business Model",
                    "🔧 Process Improvement",
                    "💡 Other"
                ], key="idea_lab_category")
            with col_priority:
                idea_priority = st.select_slider("Priority", ["Low", "Medium", "High", "🔥 Hot"], value="Medium", key="idea_priority")
            
            col_save_idea, col_develop = st.columns(2)
            with col_save_idea:
                if st.button("💾 Save Idea", use_container_width=True):
                    if idea_text.strip():
                        new_idea = {
                            'id': str(uuid.uuid4())[:8],
                            'text': idea_text,
                            'category': idea_category,
                            'priority': idea_priority,
                            'created_at': dt.now().isoformat(),
                            'status': 'New',
                            'ai_development': None,
                            'connections': []
                        }
                        st.session_state.saved_ideas.insert(0, new_idea)
                        st.success("✅ Idea saved!")
                        st.rerun()
            
            with col_develop:
                if st.button("🚀 AI Develop Idea", use_container_width=True, type="primary"):
                    replicate_token = _get_replicate_token()
                    replicate_client = get_replicate_client()
                    if idea_text.strip() and replicate_token and replicate_client:
                        with st.spinner("🤖 AI is developing your idea..."):
                            try:
                                develop_prompt = f"""You are a creative business strategist. Develop this idea into an actionable plan:

IDEA: {idea_text}
CATEGORY: {idea_category}

Provide:
1. **Refined Concept** - A polished version of the idea
2. **Target Audience** - Who would benefit most
3. **Key Features/Elements** - 3-5 core components
4. **Implementation Steps** - How to execute this
5. **Potential Challenges** - What to watch out for
6. **Success Metrics** - How to measure success
7. **Quick Win** - One thing to do TODAY to start

Be specific and actionable."""
                                
                                response = tracked_replicate_run(
                                    replicate_client,
                                    "meta/meta-llama-3-70b-instruct",
                                    {"prompt": develop_prompt, "max_tokens": 1000},
                                    operation_name="Idea Development"
                                )
                                development = "".join(response) if isinstance(response, list) else response
                                
                                new_idea = {
                                    'id': str(uuid.uuid4())[:8],
                                    'text': idea_text,
                                    'category': idea_category,
                                    'priority': idea_priority,
                                    'created_at': dt.now().isoformat(),
                                    'status': 'Developed',
                                    'ai_development': development,
                                    'connections': []
                                }
                                st.session_state.saved_ideas.insert(0, new_idea)
                                st.success("✅ Idea developed and saved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        
        with col_idea_develop:
            st.markdown("#### 🧠 AI Idea Tools")
            
            idea_tool = st.radio("Select Tool", [
                "💥 Brainstorm Variations",
                "🔗 Find Connections",
                "❓ Challenge the Idea",
                "💰 Monetization Ideas",
                "🎯 Niche Down"
            ], key="idea_tool")
            
            if st.button("⚡ Apply Tool", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if idea_text.strip() and replicate_token and replicate_client:
                    with st.spinner("Thinking..."):
                        tool_prompts = {
                            "💥 Brainstorm Variations": f"Generate 5 creative variations or pivots of this idea:\n{idea_text}",
                            "🔗 Find Connections": f"What other industries, products, or concepts could this idea connect with? Suggest 5 unexpected connections:\n{idea_text}",
                            "❓ Challenge the Idea": f"Play devil's advocate. What are the potential flaws, risks, and reasons this idea might fail? Be constructive:\n{idea_text}",
                            "💰 Monetization Ideas": f"Suggest 5 different ways to monetize or profit from this idea:\n{idea_text}",
                            "🎯 Niche Down": f"Suggest 5 specific niches or micro-markets where this idea could dominate:\n{idea_text}"
                        }
                        
                        try:
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": tool_prompts[idea_tool], "max_tokens": 600},
                                operation_name="Idea Tool"
                            )
                            result = "".join(response) if isinstance(response, list) else response
                            st.markdown(f'<div class="ai-suggestion">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            # Quick stats
            st.markdown("---")
            st.markdown("#### 📊 Idea Stats")
            total_ideas = len(st.session_state.saved_ideas)
            developed = sum(1 for i in st.session_state.saved_ideas if i.get('ai_development'))
            hot_ideas = sum(1 for i in st.session_state.saved_ideas if i.get('priority') == '🔥 Hot')
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric("Total Ideas", total_ideas)
            with col_s2:
                st.metric("Developed", developed)
        
        # Display saved ideas
        st.markdown("---")
        st.markdown("### 💡 Your Ideas")
        
        # Filter by category
        filter_cat = st.selectbox("Filter by Category", ["All"] + [
            "🛍️ Product Idea", "📢 Marketing Campaign", "🎨 Design Concept",
            "📝 Content Idea", "💼 Business Model", "🔧 Process Improvement", "💡 Other"
        ], key="idea_filter_cat")
        
        filtered_ideas = st.session_state.saved_ideas
        if filter_cat != "All":
            filtered_ideas = [i for i in filtered_ideas if i.get('category') == filter_cat]
        
        if filtered_ideas:
            for idea in filtered_ideas[:15]:
                priority_color = {"Low": "gray", "Medium": "blue", "High": "orange", "🔥 Hot": "red"}.get(idea.get('priority', 'Medium'), 'blue')
                
                with st.expander(f"{idea.get('category', '💡')} | {idea['text'][:50]}... | {idea.get('priority', 'Medium')}"):
                    st.markdown(f"**Created:** {idea['created_at'][:16].replace('T', ' ')}")
                    st.markdown(f"**Status:** {idea.get('status', 'New')}")
                    st.markdown("---")
                    st.markdown(idea['text'])
                    
                    if idea.get('ai_development'):
                        st.markdown("---")
                        st.markdown("### 🤖 AI Development")
                        st.markdown(idea['ai_development'])
                    
                    col_status, col_del_idea = st.columns([2, 1])
                    with col_status:
                        new_status = st.selectbox("Update Status", ["New", "In Progress", "Validated", "Implemented", "Archived"], 
                                                 index=["New", "In Progress", "Validated", "Implemented", "Archived"].index(idea.get('status', 'New')),
                                                 key=f"status_{idea['id']}")
                        if new_status != idea.get('status'):
                            idea['status'] = new_status
                    with col_del_idea:
                        if st.button("🗑️ Delete", key=f"del_idea_{idea['id']}"):
                            st.session_state.saved_ideas = [i for i in st.session_state.saved_ideas if i['id'] != idea['id']]
                            st.rerun()
        else:
            st.info("No ideas yet. Start capturing them above!")
    
    # ========== TAB 3: DAILY JOURNAL ==========
    with note_tabs[2]:
        st.markdown("### 📅 Daily Journal with AI Reflection")
        st.caption("Track your daily progress, mood, and let AI provide insights")
        
        col_journal, col_reflection = st.columns([2, 1])
        
        with col_journal:
            today = dt.now().strftime("%A, %B %d, %Y")
            st.markdown(f"#### 📆 {today}")
            
            # Mood tracker
            st.markdown("**How are you feeling today?**")
            mood = st.select_slider("Mood", ["😫 Rough", "😕 Meh", "😐 Okay", "🙂 Good", "😊 Great", "🚀 Amazing"], value="😐 Okay", key="daily_mood")
            
            # Journal prompts
            st.markdown("**Daily Reflection:**")
            
            journal_wins = st.text_area("🏆 Wins/Accomplishments", placeholder="What went well today? What did you accomplish?", height=80, key="journal_wins")
            journal_challenges = st.text_area("🎯 Challenges", placeholder="What challenges did you face? What could be improved?", height=80, key="journal_challenges")
            journal_gratitude = st.text_area("🙏 Gratitude", placeholder="What are you grateful for today?", height=68, key="journal_gratitude")
            journal_tomorrow = st.text_area("📋 Tomorrow's Focus", placeholder="What will you focus on tomorrow?", height=68, key="journal_tomorrow")
            
            col_save_journal, col_ai_reflect = st.columns(2)
            with col_save_journal:
                if st.button("💾 Save Journal Entry", use_container_width=True, type="primary"):
                    if any([journal_wins, journal_challenges, journal_gratitude, journal_tomorrow]):
                        entry = {
                            'id': str(uuid.uuid4())[:8],
                            'date': dt.now().strftime("%Y-%m-%d"),
                            'mood': mood,
                            'wins': journal_wins,
                            'challenges': journal_challenges,
                            'gratitude': journal_gratitude,
                            'tomorrow': journal_tomorrow,
                            'created_at': dt.now().isoformat(),
                            'ai_reflection': None
                        }
                        st.session_state.journal_entries.insert(0, entry)
                        st.success("✅ Journal entry saved!")
                        st.rerun()
            
            with col_ai_reflect:
                if st.button("🤖 AI Reflection", use_container_width=True):
                    replicate_token = _get_replicate_token()
                    replicate_client = get_replicate_client()
                    if replicate_token and replicate_client and any([journal_wins, journal_challenges]):
                        with st.spinner("AI is reflecting on your day..."):
                            try:
                                reflect_prompt = f"""As a supportive coach, provide a brief, encouraging reflection on this person's day:

Mood: {mood}
Wins: {journal_wins}
Challenges: {journal_challenges}
Gratitude: {journal_gratitude}
Tomorrow's Focus: {journal_tomorrow}

Provide:
1. Acknowledgment of their wins (be specific)
2. Perspective on challenges (reframe positively)
3. One actionable suggestion for tomorrow
4. An encouraging closing thought

Keep it warm, supportive, and under 200 words."""
                                
                                response = tracked_replicate_run(
                                    replicate_client,
                                    "meta/meta-llama-3-70b-instruct",
                                    {"prompt": reflect_prompt, "max_tokens": 400},
                                    operation_name="Journal Reflection"
                                )
                                reflection = "".join(response) if isinstance(response, list) else response
                                
                                st.markdown("### 🤖 AI Reflection")
                                st.markdown(f'<div class="ai-suggestion">{reflection}</div>', unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"Error: {e}")
        
        with col_reflection:
            st.markdown("#### 📊 Mood Tracker")
            
            if st.session_state.journal_entries:
                # Show mood history
                mood_map = {"😫 Rough": 1, "😕 Meh": 2, "😐 Okay": 3, "🙂 Good": 4, "😊 Great": 5, "🚀 Amazing": 6}
                recent_entries = st.session_state.journal_entries[:7]
                
                for entry in recent_entries:
                    st.markdown(f"{entry['date']}: {entry['mood']}")
                
                # Calculate average
                if recent_entries:
                    avg_mood = sum(mood_map.get(e['mood'], 3) for e in recent_entries) / len(recent_entries)
                    avg_emoji = ["😫", "😕", "😐", "🙂", "😊", "🚀"][min(int(avg_mood) - 1, 5)]
                    st.metric("7-Day Average", avg_emoji)
            else:
                st.info("Start journaling to track your mood!")
            
            st.markdown("---")
            st.markdown("#### 📈 Streak")
            
            # Calculate streak
            streak = 0
            if st.session_state.journal_entries:
                dates = sorted(set(e['date'] for e in st.session_state.journal_entries), reverse=True)
                today_date = dt.now().strftime("%Y-%m-%d")
                yesterday_date = (dt.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                if today_date in dates or yesterday_date in dates:
                    check_date = dt.now().date()
                    for i in range(len(dates)):
                        if check_date.strftime("%Y-%m-%d") in dates:
                            streak += 1
                            check_date -= timedelta(days=1)
                        else:
                            break
            
            st.metric("🔥 Current Streak", f"{streak} days")
        
        # Past entries
        st.markdown("---")
        st.markdown("### 📚 Past Journal Entries")
        
        if st.session_state.journal_entries:
            for entry in st.session_state.journal_entries[:10]:
                with st.expander(f"{entry['mood']} {entry['date']}"):
                    if entry.get('wins'):
                        st.markdown(f"**🏆 Wins:** {entry['wins']}")
                    if entry.get('challenges'):
                        st.markdown(f"**🎯 Challenges:** {entry['challenges']}")
                    if entry.get('gratitude'):
                        st.markdown(f"**🙏 Gratitude:** {entry['gratitude']}")
                    if entry.get('tomorrow'):
                        st.markdown(f"**📋 Tomorrow:** {entry['tomorrow']}")
                    if entry.get('ai_reflection'):
                        st.markdown("---")
                        st.info(entry['ai_reflection'])
        else:
            st.info("No journal entries yet. Start your daily reflection above!")
    
    # ========== TAB 4: GOALS & TASKS ==========
    with note_tabs[3]:
        st.markdown("### 🎯 Goals & Task Management")
        st.caption("Set goals, break them down, and track progress with AI assistance")
        
        col_goals, col_tasks = st.columns([1, 1])
        
        with col_goals:
            st.markdown("#### 🎯 Your Goals")
            
            # Add new goal
            with st.expander("➕ Add New Goal", expanded=False):
                goal_text = st.text_input("Goal", placeholder="What do you want to achieve?", key="new_goal_text")
                goal_deadline = st.date_input("Target Date", key="goal_deadline")
                goal_type = st.selectbox("Type", ["💰 Revenue", "📈 Growth", "🎨 Creative", "📚 Learning", "💪 Personal"], key="goal_type")
                
                if st.button("🎯 Create Goal", use_container_width=True):
                    if goal_text.strip():
                        new_goal = {
                            'id': str(uuid.uuid4())[:8],
                            'text': goal_text,
                            'type': goal_type,
                            'deadline': goal_deadline.isoformat(),
                            'created_at': dt.now().isoformat(),
                            'progress': 0,
                            'tasks': [],
                            'status': 'Active'
                        }
                        st.session_state.journal_goals.insert(0, new_goal)
                        st.success("Goal created!")
                        st.rerun()
            
            # AI Goal Breakdown
            if st.button("🤖 AI: Break Down a Goal", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if goal_text.strip() and replicate_token and replicate_client:
                    with st.spinner("AI is creating your action plan..."):
                        try:
                            breakdown_prompt = f"""Break this goal into specific, actionable tasks:

GOAL: {goal_text}
DEADLINE: {goal_deadline}
TYPE: {goal_type}

Create a step-by-step action plan with:
1. 5-7 specific tasks to achieve this goal
2. Estimated time for each task
3. Dependencies between tasks
4. Quick wins to build momentum

Format as a numbered list with clear, actionable items."""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": breakdown_prompt, "max_tokens": 600},
                                operation_name="Goal Breakdown"
                            )
                            breakdown = "".join(response) if isinstance(response, list) else response
                            st.markdown("### 📋 AI Action Plan")
                            st.markdown(breakdown)
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            # Display goals
            st.markdown("---")
            for goal in st.session_state.journal_goals[:5]:
                with st.container():
                    st.markdown(f"**{goal['type']} {goal['text'][:40]}...**")
                    st.progress(goal.get('progress', 0) / 100)
                    
                    col_prog, col_status = st.columns([2, 1])
                    with col_prog:
                        new_progress = st.slider("Progress", 0, 100, goal.get('progress', 0), key=f"prog_{goal['id']}")
                        if new_progress != goal.get('progress'):
                            goal['progress'] = new_progress
                    with col_status:
                        if goal.get('progress', 0) >= 100:
                            st.success("✅ Complete!")
        
        with col_tasks:
            st.markdown("#### ✅ Quick Tasks")
            
            # Add quick task
            task_text = st.text_input("New Task", placeholder="What needs to be done?", key="quick_task_input")
            if st.button("➕ Add Task", use_container_width=True):
                if task_text.strip():
                    if 'quick_tasks' not in st.session_state:
                        st.session_state.quick_tasks = []
                    st.session_state.quick_tasks.append({
                        'id': str(uuid.uuid4())[:8],
                        'text': task_text,
                        'done': False,
                        'created_at': dt.now().isoformat()
                    })
                    st.rerun()
            
            # Display tasks
            st.markdown("---")
            if 'quick_tasks' not in st.session_state:
                st.session_state.quick_tasks = []
            
            for task in st.session_state.quick_tasks[:15]:
                col_check, col_task, col_del = st.columns([1, 6, 1])
                with col_check:
                    done = st.checkbox("", value=task.get('done', False), key=f"task_{task['id']}")
                    if done != task.get('done'):
                        task['done'] = done
                with col_task:
                    style = "text-decoration: line-through; color: gray;" if task.get('done') else ""
                    st.markdown(f"<span style='{style}'>{task['text']}</span>", unsafe_allow_html=True)
                with col_del:
                    if st.button("×", key=f"del_task_{task['id']}"):
                        st.session_state.quick_tasks = [t for t in st.session_state.quick_tasks if t['id'] != task['id']]
                        st.rerun()
            
            # Task stats
            if st.session_state.quick_tasks:
                done_count = sum(1 for t in st.session_state.quick_tasks if t.get('done'))
                total = len(st.session_state.quick_tasks)
                st.markdown(f"**{done_count}/{total} completed**")
                
                if st.button("🧹 Clear Completed"):
                    st.session_state.quick_tasks = [t for t in st.session_state.quick_tasks if not t.get('done')]
                    st.rerun()
    
    # ========== TAB 5: SEARCH & INSIGHTS ==========
    with note_tabs[4]:
        st.markdown("### 🔍 Search & AI Insights")
        st.caption("Search across all your notes, ideas, and journals with AI-powered analysis")
        
        # Global search
        global_search = st.text_input("🔍 Search everything...", placeholder="Search notes, ideas, journal entries...", key="global_journal_search")
        
        if global_search:
            results = []
            
            # Search notes
            for note in st.session_state.saved_notes:
                if global_search.lower() in note.get('text', '').lower() or global_search.lower() in note.get('title', '').lower():
                    results.append({'type': '📝 Note', 'content': note.get('title', note['text'][:50]), 'date': note['created_at'], 'data': note})
            
            # Search ideas
            for idea in st.session_state.saved_ideas:
                if global_search.lower() in idea.get('text', '').lower():
                    results.append({'type': '💡 Idea', 'content': idea['text'][:50], 'date': idea['created_at'], 'data': idea})
            
            # Search journal
            for entry in st.session_state.journal_entries:
                searchable = f"{entry.get('wins', '')} {entry.get('challenges', '')} {entry.get('gratitude', '')}"
                if global_search.lower() in searchable.lower():
                    results.append({'type': '📅 Journal', 'content': entry['date'], 'date': entry['created_at'], 'data': entry})
            
            st.markdown(f"**Found {len(results)} results:**")
            for result in results[:20]:
                with st.expander(f"{result['type']}: {result['content']}..."):
                    st.json(result['data'])
        
        st.markdown("---")
        
        # AI Insights
        st.markdown("### 🧠 AI Insights")
        
        col_insight1, col_insight2 = st.columns(2)
        
        with col_insight1:
            if st.button("📊 Analyze My Patterns", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if replicate_token and replicate_client and (st.session_state.saved_notes or st.session_state.journal_entries):
                    with st.spinner("Analyzing your patterns..."):
                        try:
                            # Compile data
                            all_content = []
                            for note in st.session_state.saved_notes[:10]:
                                all_content.append(f"Note: {note.get('text', '')[:200]}")
                            for entry in st.session_state.journal_entries[:7]:
                                all_content.append(f"Journal ({entry['mood']}): Wins: {entry.get('wins', '')} Challenges: {entry.get('challenges', '')}")
                            
                            analysis_prompt = f"""Analyze these personal notes and journal entries to identify:

1. **Recurring Themes** - What topics come up repeatedly?
2. **Mood Patterns** - Any trends in emotional state?
3. **Strengths** - What does this person do well?
4. **Growth Areas** - Where could they improve?
5. **Recommendations** - 3 specific suggestions

Content to analyze:
{chr(10).join(all_content[:15])}

Be insightful but supportive."""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": analysis_prompt, "max_tokens": 800},
                                operation_name="Content Analysis"
                            )
                            analysis = "".join(response) if isinstance(response, list) else response
                            st.markdown(analysis)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("Add more notes and journal entries for pattern analysis")
        
        with col_insight2:
            if st.button("💡 Connect My Ideas", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if replicate_token and replicate_client and len(st.session_state.saved_ideas) >= 2:
                    with st.spinner("Finding connections..."):
                        try:
                            ideas_text = [idea['text'][:150] for idea in st.session_state.saved_ideas[:10]]
                            
                            connect_prompt = f"""Look at these ideas and find unexpected connections between them:

Ideas:
{chr(10).join([f'{i+1}. {idea}' for i, idea in enumerate(ideas_text)])}

Find:
1. **Common Threads** - What connects these ideas?
2. **Synergies** - Which ideas could be combined?
3. **Meta-Idea** - One overarching idea that encompasses several
4. **Action Item** - One thing to do based on these connections"""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": connect_prompt, "max_tokens": 600},
                                operation_name="Idea Connection"
                            )
                            connections = "".join(response) if isinstance(response, list) else response
                            st.markdown(connections)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("Add at least 2 ideas to find connections")
        
        # Export section
        st.markdown("---")
        st.markdown("### 📤 Export Your Data")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            if st.session_state.saved_notes:
                notes_export = json.dumps(st.session_state.saved_notes, indent=2, default=str)
                st.download_button("📝 Export Notes", notes_export, "notes_export.json", "application/json", use_container_width=True)
        
        with col_exp2:
            if st.session_state.saved_ideas:
                ideas_export = json.dumps(st.session_state.saved_ideas, indent=2, default=str)
                st.download_button("💡 Export Ideas", ideas_export, "ideas_export.json", "application/json", use_container_width=True)
        
        with col_exp3:
            if st.session_state.journal_entries:
                journal_export = json.dumps(st.session_state.journal_entries, indent=2, default=str)
                st.download_button("📅 Export Journal", journal_export, "journal_export.json", "application/json", use_container_width=True)
