import streamlit as st


def render_task_queue_tab(
    enhanced_available, replicate_api, printify_api, shopify_api, youtube_api
):
    """
    Renders the Task Queue tab (Tab 2).
    """
    # Use enhanced task queue if available, otherwise fall back to original
    if enhanced_available:
        try:
            from app.services.task_queue_engine import render_enhanced_task_queue

            render_enhanced_task_queue(
                replicate_api=replicate_api,
                printify_api=printify_api,
                shopify_api=shopify_api,
                youtube_api=youtube_api,
            )
        except ImportError:
            st.error("Enhanced Task Queue module not found.")
    else:
        # Fallback: simple task list UI when enhanced task queue is not available
        st.markdown("### 📋 Task Queue")
        st.info("The enhanced task queue engine is not available. Showing basic task list.")

        if "task_list" not in st.session_state:
            st.session_state.task_list = []

        new_task = st.text_input("Add a new task:", key="new_task_input")
        if st.button("➕ Add Task") and new_task:
            st.session_state.task_list.append({"name": new_task, "done": False})
            st.rerun()

        for i, task in enumerate(st.session_state.task_list):
            col1, col2 = st.columns([4, 1])
            with col1:
                done = st.checkbox(task["name"], value=task["done"], key=f"task_{i}")
                st.session_state.task_list[i]["done"] = done
            with col2:
                if st.button("🗑️", key=f"del_task_{i}"):
                    st.session_state.task_list.pop(i)
                    st.rerun()

        if not st.session_state.task_list:
            st.caption("No tasks yet. Add one above!")
