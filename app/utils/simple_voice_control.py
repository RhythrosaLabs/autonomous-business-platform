"""
Simple Local Voice Control for Otto (No Amazon Account Required!)
Uses Python speech recognition library with your Mac's microphone
"""

import speech_recognition as sr
import threading
import queue
import logging
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleVoiceControl:
    """Simple local voice control using Python speech recognition"""
    
    def __init__(self, on_command_callback: Optional[Callable] = None):
        """
        Initialize simple voice control
        
        Args:
            on_command_callback: Function to call when command is heard
        """
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.listen_thread = None
        self.command_queue = queue.Queue()
        self.on_command = on_command_callback
        
        # New: Message composition state
        self.message_active = False
        self.current_message = []
        self.last_activity = None
        
        # Find MacBook microphone (avoid virtual audio devices)
        try:
            mic_list = sr.Microphone.list_microphone_names()
            mic_index = None
            
            # Try to find MacBook built-in microphone
            for index, name in enumerate(mic_list):
                if "macbook" in name.lower() and "microphone" in name.lower():
                    mic_index = index
                    logger.info(f"Found MacBook microphone: {name}")
                    break
            
            # If not found, try any microphone that's not a virtual device
            if mic_index is None:
                virtual_keywords = ["blackhole", "virtual", "aggregate", "bridge", "serato", "multi-output"]
                for index, name in enumerate(mic_list):
                    if not any(keyword in name.lower() for keyword in virtual_keywords):
                        if "microphone" in name.lower() or "input" in name.lower():
                            mic_index = index
                            logger.info(f"Using microphone: {name}")
                            break
            
            if mic_index is not None:
                self.microphone = sr.Microphone(device_index=mic_index)
            else:
                self.microphone = sr.Microphone()  # Fallback to default
                logger.warning("Using default microphone")
            
            # Adjust for ambient noise
            with self.microphone as source:
                logger.info("🎤 Adjusting for ambient noise... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
            # Optimize recognizer settings for better detection
            self.recognizer.energy_threshold = 300  # Lower = more sensitive
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8  # Seconds of silence to end phrase
            
            logger.info(f"✅ Voice control ready! Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Could not initialize microphone: {e}")
    
    def start_listening(self):
        """Start listening for voice commands in background"""
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        if not self.microphone:
            logger.error("Microphone not available")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info("🎤 Started listening for voice commands!")
        logger.info("Say 'Hey Otto' followed by your command")
    
    def stop_listening(self):
        """Stop listening for voice commands"""
        self.is_listening = False
        self.message_active = False
        self.current_message = []
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        logger.info("🔇 Stopped listening")
    
    def get_message_state(self):
        """Get current message composition state"""
        return {
            'active': self.message_active,
            'message': " ".join(self.current_message) if self.current_message else "",
            'last_activity': self.last_activity
        }
    
    def _listen_loop(self):
        """Background loop that listens for voice"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    if self.message_active:
                        logger.info("🎤 Recording message... (Say 'send message' when done)")
                    else:
                        logger.info("🎤 Listening for 'Hey Otto'...")
                    
                    # Listen for audio with longer timeout
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                
                try:
                    # Recognize speech using Google's free service
                    text = self.recognizer.recognize_google(audio).lower()
                    logger.info(f"🎤 Heard: '{text}'")
                    self.last_activity = datetime.now()
                    
                    # Check for send command
                    if "send message" in text or "send it" in text or "submit" in text:
                        if self.message_active and self.current_message:
                            # Combine all message parts
                            full_message = " ".join(self.current_message)
                            logger.info(f"✅ Sending message: '{full_message}'")
                            
                            # Put in queue
                            self.command_queue.put({
                                'text': full_message,
                                'timestamp': datetime.now().isoformat(),
                                'raw': text,
                                'type': 'complete'
                            })
                            
                            # Call callback if provided
                            if self.on_command:
                                try:
                                    self.on_command(full_message)
                                    logger.info(f"✅ Message sent to chat: '{full_message}'")
                                except Exception as e:
                                    logger.error(f"Error in command callback: {e}")
                            
                            # Reset message state
                            self.message_active = False
                            self.current_message = []
                        else:
                            logger.warning("⚠️ 'Send message' detected but no message recorded")
                        continue
                    
                    # Check for cancel command
                    if self.message_active and ("cancel" in text or "clear" in text or "nevermind" in text):
                        logger.info("🚫 Message cancelled")
                        self.message_active = False
                        self.current_message = []
                        continue
                    
                    # Check if it starts with wake word
                    if "hey otto" in text or text.startswith("otto"):
                        # Activate message composition mode
                        self.message_active = True
                        self.current_message = []
                        
                        # Extract any command that came after wake word
                        command = text.replace("hey otto", "").replace("otto", "").strip()
                        
                        if command:
                            # Remove "send message" if it's in there
                            command = command.replace("send message", "").replace("send it", "").strip()
                            if command:
                                self.current_message.append(command)
                                logger.info(f"✅ Message started: '{command}' (Say more or 'send message')")
                        else:
                            logger.info("✅ Message recording activated (Start speaking your command)")
                    
                    # If message is active, append to current message
                    elif self.message_active:
                        # Filter out send commands
                        text_clean = text.replace("send message", "").replace("send it", "").strip()
                        if text_clean:
                            self.current_message.append(text_clean)
                            logger.info(f"📝 Added to message: '{text_clean}'")
                    else:
                        logger.debug(f"Speech heard but no wake word: '{text}'")
                    
                except sr.UnknownValueError:
                    logger.debug("Could not understand audio")
                except sr.RequestError as e:
                    logger.error(f"Speech recognition service error: {e}")
                    logger.error("Check your internet connection - Google Speech Recognition requires internet")
            
            except sr.WaitTimeoutError:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                if self.is_listening:
                    # Wait a bit before retrying
                    import time
                    time.sleep(1)
    
    def get_recent_commands(self, limit: int = 10) -> list:
        """Get recent commands from queue"""
        commands = []
        try:
            while not self.command_queue.empty() and len(commands) < limit:
                commands.append(self.command_queue.get_nowait())
        except queue.Empty:
            pass
        return commands

def render_simple_voice_control(session_state):
    """Render simple voice control UI in Streamlit"""
    import streamlit as st
    
    st.subheader("🎤 Simple Voice Control (No Account Needed!)")
    
    # Quick start guide
    st.info("""
    **🚀 Quick Start:**
    1. Click "🎤 Start Listening" below
    2. Say **"Hey Otto"** to start recording
    3. Speak your command (e.g., "create a campaign about coffee")
    4. Say **"send message"** to execute
    """)
    
    st.markdown("""
    **Use your Mac's microphone** - no Amazon account required!
    
    Just say **"Hey Otto"** followed by your command, then **"send message"** to execute.
    """)
    
    # Initialize voice control
    if 'simple_voice_control' not in session_state:
        def handle_command(command_text):
            """Handle incoming voice command - send to chat assistant"""
            if 'voice_commands_list' not in st.session_state:
                st.session_state.voice_commands_list = []
            
            # Add to command history
            st.session_state.voice_commands_list.append({
                'command': command_text,
                'timestamp': datetime.now().isoformat(),
                'status': 'received'
            })
            
            # Send to chat assistant (use chat_history not messages!)
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user",
                "content": command_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Trigger chat to process command
            st.session_state.voice_command_pending = True
            st.session_state.process_voice_command = command_text
        
        session_state.simple_voice_control = SimpleVoiceControl(
            on_command_callback=handle_command
        )
    
    voice_control = session_state.simple_voice_control
    
    # Check for pending voice commands and provide navigation
    if session_state.get('voice_command_pending'):
        st.success("✅ Voice command sent to Otto!")
        st.info("💬 **Go to the Chat tab in the sidebar** to see Otto's response and the command executing.")
        
        if st.button("➡️ Open Chat Now", use_container_width=True, type="primary"):
            # Try to switch to chat tab - this works if chat is in sidebar
            st.session_state.voice_command_pending = False
            st.rerun()
        
        if st.button("✅ Dismiss", use_container_width=True):
            st.session_state.voice_command_pending = False
            st.rerun()
    
    # Show message composition state
    message_state = voice_control.get_message_state()
    if message_state['active']:
        st.success("🎙️ **RECORDING MESSAGE** - Keep speaking or say 'send message' when done")
        if message_state['message']:
            st.info(f"📝 Current message: _{message_state['message']}_")
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not voice_control.is_listening:
            if st.button("🎤 Start Listening", use_container_width=True, type="primary"):
                voice_control.start_listening()
                st.success("Started listening! Say 'Hey Otto' to begin composing a message.")
                st.rerun()
        else:
            if st.button("🔇 Stop Listening", use_container_width=True):
                voice_control.stop_listening()
                st.rerun()
    
    with col2:
        if message_state['active']:
            if st.button("📤 Send Now", use_container_width=True, type="primary"):
                # Manually trigger send
                if voice_control.current_message:
                    full_message = " ".join(voice_control.current_message)
                    if voice_control.on_command:
                        voice_control.on_command(full_message)
                    voice_control.message_active = False
                    voice_control.current_message = []
                    st.success(f"Sent: {full_message}")
                    st.rerun()
    
    with col3:
        if message_state['active']:
            if st.button("🚫 Cancel", use_container_width=True):
                voice_control.message_active = False
                voice_control.current_message = []
                st.warning("Message cancelled")
                st.rerun()
    
    # Status
    if voice_control.is_listening:
        st.success("🎤 **LISTENING** - Always on, perpetually listening")
    else:
        st.info("Voice control inactive")
    
    # Status
    st.divider()
    st.write("**Status:**")
    
    if voice_control.microphone:
        st.success("✅ Microphone detected and ready")
    else:
        st.error("❌ Microphone not available - check System Preferences → Security & Privacy → Microphone")
    
    # Example commands
    st.divider()
    st.write("**🎯 How to Use Voice Commands:**")
    
    st.markdown("""
    **Step 1:** Click "🎤 Start Listening" (stays on perpetually)
    
    **Step 2:** Say **"Hey Otto"** to start composing a message
    
    **Step 3:** Speak your command (you can speak multiple sentences)
    
    **Step 4:** Say **"send message"** to send it for execution
    
    ---
    
    **Example conversation:**
    - You: "Hey Otto"
    - Otto: _(starts recording)_
    - You: "Create a campaign about sustainable coffee"
    - You: "Make it focus on eco-friendly packaging"
    - You: "Target millennial consumers"
    - You: "Send message"
    - Otto: _(executes command in chat)_
    
    ---
    
    **Voice Triggers:**
    - 🎙️ **"Hey Otto"** - Start message composition
    - 📤 **"Send message"** - Execute the message
    - 📤 **"Send it"** - Alternative send command
    - 🚫 **"Cancel"** - Discard current message
    - 🚫 **"Clear"** - Discard current message
    """)
    
    st.divider()
    st.write("**Example Commands:**")
    
    examples = {
        "🎬 Campaign": "Hey Otto... create a campaign about sustainable fashion for Gen Z audience... include social media posts and video... send message",
        "🖼️ Images": "Hey Otto... generate 5 product images of coffee mugs with minimalist designs... send message",
        "🎥 Videos": "Hey Otto... make a 30 second video about productivity tips for remote workers... send message",
        "📝 Content": "Hey Otto... write a blog post about AI automation trends in 2026... make it 1000 words... send message",
        "💌 Email": "Hey Otto... compose an outreach email to tech influencers about our new product launch... send message",
    }
    
    for category, example in examples.items():
        with st.expander(category):
            st.caption(f"_{example}_")
    
    # Recent commands
    st.divider()
    st.write("**Recent Voice Commands:**")
    
    if 'voice_commands_list' in session_state and session_state.voice_commands_list:
        for cmd in reversed(session_state.voice_commands_list[-10:]):
            with st.container():
                col_time, col_cmd, col_status = st.columns([0.15, 0.7, 0.15])
                with col_time:
                    time_str = cmd['timestamp'].split('T')[1][:8] if 'T' in cmd['timestamp'] else cmd['timestamp']
                    st.caption(f"🕐 {time_str}")
                with col_cmd:
                    st.write(f"🎤 _{cmd['command']}_")
                with col_status:
                    st.success("✅")
        
        # Clear history button
        if st.button("🧹 Clear History", use_container_width=True):
            session_state.voice_commands_list = []
            st.rerun()
    else:
        st.info("""
        No commands yet. Try this:
        1. Click "Start Listening"
        2. Say "Hey Otto"
        3. Say "create a campaign about coffee"
        4. Say "send message"
        """)
    
    # Test microphone button
    st.divider()
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        if st.button("🧪 Test Microphone", use_container_width=True):
            with st.spinner("🎤 Speak now for 3 seconds..."):
                try:
                    import speech_recognition as sr
                    r = sr.Recognizer()
                    with sr.Microphone(device_index=1) as source:
                        st.info("🗣️ SAY SOMETHING NOW!")
                        audio = r.listen(source, timeout=3, phrase_time_limit=3)
                        st.info("Processing...")
                        text = r.recognize_google(audio)
                        st.success(f"✅ Heard: '{text}'")
                except sr.WaitTimeoutError:
                    st.warning("⏱️ No speech detected - try speaking louder")
                except sr.UnknownValueError:
                    st.warning("❌ Could not understand - speak clearly and try again")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with col_test2:
        if st.button("🔊 Check Mic Permissions", use_container_width=True):
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=1,
                    frames_per_buffer=1024
                )
                data = stream.read(1024, exception_on_overflow=False)
                stream.stop_stream()
                stream.close()
                p.terminate()
                st.success("✅ Microphone permissions OK!")
            except OSError:
                st.error("❌ Permission denied! Enable in System Preferences → Security & Privacy → Microphone")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Installation instructions
    with st.expander("📦 Setup & Troubleshooting Guide"):
        st.markdown("""
        ### ✅ First Time Setup:
        
        **1. Install dependencies:**
        ```bash
        pip install SpeechRecognition pyaudio
        ```
        
        **2. On Mac, install PortAudio:**
        ```bash
        brew install portaudio
        pip install pyaudio
        ```
        
        **3. Grant microphone permission:**
        - System Preferences → Security & Privacy → Privacy tab
        - Click "Microphone" in left sidebar
        - Enable checkbox for Terminal (if running from terminal)
        - Enable checkbox for Python
        
        ---
        
        ### 🧪 Test Your Setup:
        
        Run this test from terminal:
        ```bash
        cd /Users/sheils/repos/printify
        python test_voice.py
        ```
        
        This will:
        - ✅ Detect your microphone
        - 🎤 Test if it can hear you
        - 🔍 Show which microphone is being used
        
        ---
        
        ### 🔧 Troubleshooting:
        
        **"Microphone not available"**
        - Check System Preferences → Security & Privacy → Microphone
        - Restart the app after granting permissions
        - Try running: `python test_voice.py` to diagnose
        
        **"Could not understand audio"**
        - Speak clearly and not too fast
        - Ensure you're using the actual MacBook microphone (not BlackHole/virtual device)
        - Check internet connection (Google Speech Recognition needs internet)
        - Try the Test Microphone button above
        
        **Commands not being processed**
        - Make sure to say "Hey Otto" before your command
        - Example: "Hey Otto, create a campaign about coffee"
        - Check Recent Voice Commands section to see if command was heard
        - Go to Chat tab to see the response
        
        **Using external microphone**
        - Plug in microphone before starting the app
        - Restart voice control after connecting microphone
        - Use `python test_voice.py` to verify correct mic is selected
        
        ---
        
        ### 🎯 How the New System Works:
        
        **Perpetual Listening Mode:**
        - Click "Start Listening" once - it stays on indefinitely
        - Always listening in the background for "Hey Otto"
        - No need to click buttons between commands
        
        **Two-Stage Command System:**
        1. **Say "Hey Otto"** → Activates message recording (green indicator appears)
        2. **Speak your full command** - Can be multiple sentences, take your time
        3. **Say "Send message"** → Executes the command and sends to Chat
        
        **Why this approach?**
        - Build complex multi-part commands naturally
        - Review what you've said before sending (check "Current message" preview)
        - Cancel or edit if you make a mistake
        - More like having a conversation
        
        **Alternative send triggers:**
        - "Send message" ✅
        - "Send it" ✅
        - "Submit" ✅
        - Click the "📤 Send Now" button ✅
        
        **Cancel commands:**
        - Say "Cancel", "Clear", or "Nevermind"
        - Or click the "🚫 Cancel" button
        
        ### 💡 Pro Tips:
        - Leave listening on all day - it only activates on "Hey Otto"
        - Speak naturally - you can pause between sentences
        - Build long commands: "Hey Otto... create campaign... make it about tech... target developers... send message"
        - Check the current message preview to see what's been captured
        - Internet connection required for speech recognition
        """)
        
        # Show current microphone info
        st.divider()
        st.write("**Current Microphone Info:**")
        try:
            import speech_recognition as sr
            mic_list = sr.Microphone.list_microphone_names()
            if voice_control.microphone:
                # Try to figure out which mic index is being used
                st.code(f"Total microphones detected: {len(mic_list)}")
                st.caption("If voice isn't working, the wrong microphone may be selected. Look for 'BlackHole' or virtual devices.")
        except:
            pass
