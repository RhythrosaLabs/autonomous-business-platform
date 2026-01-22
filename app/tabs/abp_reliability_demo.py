"""
Demo tab showcasing enhanced reliability features
Progress tracking, error recovery, validation, and state management
"""

import streamlit as st
import time
import random
from pathlib import Path
import sys

# Add utils to path
utils_path = Path(__file__).parent.parent / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from progress_tracking import CancellableProgress, create_progress_tracker
from error_recovery import (
    retry_with_backoff,
    PartialSuccessHandler,
    batch_process_with_recovery,
    OperationResult
)
from state_management import AutosaveManager, TransactionManager, get_crash_recovery
from validation import APIValidator, InputValidator


def demo_progress_tracking():
    """Demonstrate cancellable progress tracking"""
    st.header("🎯 Progress Tracking Demo")
    st.caption("Cancellable operations with ETA and detailed progress")
    
    if st.button("▶️ Run Demo Operation", type="primary"):
        progress = create_progress_tracker(
            operation_name="Demo Operation",
            total_steps=100,
            show_controls=True
        )
        progress.start()
        
        steps = [
            ("Initializing", 20),
            ("Processing data", 30),
            ("Generating content", 40),
            ("Finalizing", 10)
        ]
        
        current = 0
        for step_name, duration in steps:
            step = progress.start_step(step_name)
            
            for i in range(duration):
                if progress.is_cancelled():
                    st.warning("Operation was cancelled by user")
                    return
                
                time.sleep(0.1)  # Simulate work
                current += 1
                progress.update(current)
            
            progress.complete_step(f"Completed {step_name}")
        
        progress.complete("✅ Demo completed successfully!")
        st.balloons()


def demo_error_recovery():
    """Demonstrate error recovery and retry logic"""
    st.header("🔄 Error Recovery Demo")
    st.caption("Automatic retry with exponential backoff")
    
    # Simulate flaky API
    failure_rate = st.slider("API Failure Rate (%)", 0, 100, 50)
    
    if st.button("🎲 Test Flaky API Call"):
        
        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.5,
            on_retry=lambda attempt, delay, error: st.warning(
                f"⚠️ Retry {attempt}/3 after {delay:.1f}s: {str(error)}"
            )
        )
        def flaky_api_call():
            if random.randint(1, 100) <= failure_rate:
                raise Exception("API temporarily unavailable")
            return {"status": "success", "data": "Hello World"}
        
        try:
            with st.spinner("Calling API..."):
                result = flaky_api_call()
            st.success(f"✅ Success: {result}")
        except Exception as e:
            st.error(f"❌ Failed after all retries: {str(e)}")


def demo_partial_success():
    """Demonstrate partial success handling"""
    st.header("✓ Partial Success Demo")
    st.caption("Batch operations that track individual item success/failure")
    
    num_items = st.number_input("Number of items to process", 5, 50, 10)
    failure_rate = st.slider("Item Failure Rate (%)", 0, 100, 20, key="partial_failure_rate")
    
    if st.button("📦 Process Batch"):
        
        def process_item(item):
            time.sleep(0.1)  # Simulate work
            if random.randint(1, 100) <= failure_rate:
                raise Exception(f"Processing failed for item {item}")
            return f"Result_{item}"
        
        items = [f"Item_{i}" for i in range(num_items)]
        
        result = batch_process_with_recovery(
            items=items,
            process_func=process_item,
            operation_name="Batch Processing",
            show_progress=True,
            continue_on_error=True
        )
        
        # Display detailed results
        st.markdown(f"### Results: {result.get_summary()}")
        st.metric("Success Rate", f"{result.success_rate * 100:.1f}%")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Succeeded", len(result.partial_results))
        with col2:
            st.metric("❌ Failed", len(result.failed_items))
        
        if result.failed_items:
            with st.expander("🔍 Failed Items"):
                for item, error in result.failed_items:
                    st.error(f"**{item}**: {error}")


def demo_transaction_rollback():
    """Demonstrate transaction rollback"""
    st.header("↩️ Transaction Rollback Demo")
    st.caption("Atomic file operations with rollback on failure")
    
    workspace = Path.cwd() / "demo_workspace"
    workspace.mkdir(exist_ok=True)
    
    if st.button("🎲 Test Transaction"):
        transaction = TransactionManager(workspace)
        transaction.begin_transaction("demo")
        
        try:
            # Create some files
            st.info("Creating files...")
            transaction.create_file(workspace / "file1.txt", "Content 1")
            transaction.create_file(workspace / "file2.txt", "Content 2")
            time.sleep(0.5)
            
            # Simulate random failure
            if random.random() < 0.5:
                raise Exception("Simulated error during transaction")
            
            # Commit if successful
            transaction.commit()
            st.success("✅ Transaction committed! Files created.")
            
        except Exception as e:
            st.error(f"❌ Error occurred: {str(e)}")
            st.warning("⏮️ Rolling back transaction...")
            transaction.rollback()
            st.info("✓ Transaction rolled back - all changes reverted")


def demo_autosave():
    """Demonstrate autosave functionality"""
    st.header("💾 Autosave Demo")
    st.caption("Automatic state persistence with recovery")
    
    autosave = AutosaveManager()
    
    # Show saved states
    states = autosave.list_saved_states()
    if states:
        st.metric("Saved States", len(states))
        
        with st.expander("📋 View Saved States"):
            for state in states[:5]:  # Show last 5
                st.text(f"{state.timestamp}: {state.operation}")
    
    # Manual save
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Current State"):
            state_data = {
                'current_tab': 'demo',
                'timestamp': time.time(),
                'demo_data': 'test'
            }
            autosave.save_state(state_data, operation="manual_demo")
            st.success("✅ State saved!")
    
    with col2:
        if st.button("📂 Load Latest State"):
            latest = autosave.load_latest_state()
            if latest:
                st.json(latest.state_data)
            else:
                st.info("No saved states found")


def demo_input_validation():
    """Demonstrate input validation"""
    st.header("✅ Input Validation Demo")
    st.caption("Real-time validation for user inputs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Email Validation")
        email = st.text_input("Email", key="demo_email")
        if email:
            result = InputValidator.validate_email(email)
            if result.is_valid:
                st.success(result.message)
            else:
                st.error(result.message)
    
    with col2:
        st.subheader("Number Validation")
        number = st.text_input("Age (18-100)", key="demo_age")
        if number:
            result = InputValidator.validate_number(
                number,
                min_val=18,
                max_val=100,
                field_name="Age"
            )
            if result.is_valid:
                st.success(result.message)
            else:
                st.error(result.message)


def render():
    """Main render function"""
    st.title("🚀 Enhanced Reliability Features")
    st.markdown("""
    This demo showcases the new reliability and user experience features:
    - ✅ Input validation with real-time feedback
    - 🔄 Automatic retry with exponential backoff
    - 🎯 Cancellable progress tracking with ETA
    - ↩️ Transaction rollback for atomic operations
    - ✓ Partial success handling for batch operations
    - 💾 Autosave and crash recovery
    """)
    
    st.divider()
    
    tabs = st.tabs([
        "🎯 Progress",
        "🔄 Retry",
        "✓ Partial Success",
        "↩️ Rollback",
        "💾 Autosave",
        "✅ Validation"
    ])
    
    with tabs[0]:
        demo_progress_tracking()
    
    with tabs[1]:
        demo_error_recovery()
    
    with tabs[2]:
        demo_partial_success()
    
    with tabs[3]:
        demo_transaction_rollback()
    
    with tabs[4]:
        demo_autosave()
    
    with tabs[5]:
        demo_input_validation()
    
    st.divider()
    
    st.info("""
    💡 **Integration Notes:**
    These utilities are now available throughout the platform and can be integrated into:
    - Campaign generation (partial success tracking)
    - API calls (retry logic and validation)
    - File operations (transaction rollback)
    - Long-running tasks (cancellable progress)
    - Settings pages (connection testing)
    """)


if __name__ == "__main__":
    render()
