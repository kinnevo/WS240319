def start_new_session():
    """
    Start a new session with LangFlow.
    
    Returns:
        str: The session ID if successful, None otherwise
    """
    # Session creation endpoint
    session_url = f"{BASE_API_URL}/api/v1/sessions"
    
    # Payload for creating a new session
    payload = {
        "flow_id": FLOW_ID,
        "inputs": {}  # Initial inputs if any
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {APPLICATION_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make the request to create a session
        response = requests.post(session_url, json=payload, headers=headers)
        
        if response.status_code == 200 or response.status_code == 201:
            session_data = response.json()
            session_id = session_data.get('session_id')
            
            # Store session information
            st.session_state.sessions[session_id] = {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "conversation": [],
                "last_agent": None,
                "agents_used": set()
            }
            
            return session_id
        else:
            st.error(f"Failed to create session: {response.status_code}")
            st.error(response.text)
            return None
    except Exception as e:
        st.error(f"Error creating session: {str(e)}")
        return None
    
import requests
import streamlit as st
from dotenv import load_dotenv
import os
import json
import pandas as pd
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# LangFlow connection settings
BASE_API_URL = "http://34.59.108.214:7860/"
FLOW_ID = "4d3b8a75-21a4-4ce7-b41d-2f70aa6e3fdd"
APPLICATION_TOKEN = os.environ.get("OPENAI_API_KEY")
ENDPOINT = "4d3b8a75-21a4-4ce7-b41d-2f70aa6e3fdd"  # The endpoint name of the flow

# Initialize session state for conversation memory, agent tracking, and sessions
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Initialize agent tracking
if 'agents' not in st.session_state:
    st.session_state.agents = {
        "Agent_1": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "Agent_2": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "Agent_3": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False}
    }

# Initialize sessions tracking
if 'sessions' not in st.session_state:
    st.session_state.sessions = {}

# Initialize current session ID
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None

# Available agent statuses: "Idle", "Active", "Completed", "Failed"

def run_flow(message: str, agent_name: str = "Agent_1", history: list = None, session_id: str = None) -> dict:
    """
    Run the LangFlow with the given message and conversation history.
    
    Args:
        message: The current user message
        agent_name: The name of the agent to use
        history: Optional list of previous conversation messages
        session_id: Optional session ID for session tracking
    
    Returns:
        The response from LangFlow
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{ENDPOINT}"
    
    # Update agent status
    update_agent_status(agent_name, "Active")
    
    # Track agent usage in session
    if session_id and session_id in st.session_state.sessions:
        st.session_state.sessions[session_id]["last_agent"] = agent_name
        st.session_state.sessions[session_id]["agents_used"].add(agent_name)
    
    # Build the payload
    payload = {
        "input_value": message,
        "output_type": "chat",
        "input_type": "chat",
        "agent": agent_name  # Pass the agent name to LangFlow
    }
    
    # Include session ID if provided
    if session_id:
        payload["session_id"] = session_id
    
    # Include conversation history if available
    if history and len(history) > 0:
        # Format history in the way LangFlow expects it
        formatted_history = json.dumps(history)
        payload["conversation_history"] = formatted_history

    headers = {"Authorization": f"Bearer {APPLICATION_TOKEN}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response_data = response.json()
        
        # Check if exploration was completed based on response
        # You'll need to adapt this logic based on how your LangFlow indicates completion
        if "full_exploration_completed" in response_data or "exploration_status" in response_data:
            exploration_completed = response_data.get("full_exploration_completed", False)
            if exploration_completed:
                update_agent_exploration(agent_name, True)
            
        # Update agent status to completed
        update_agent_status(agent_name, "Completed")
        
        # Increment exploration counter
        increment_agent_exploration(agent_name)
        
        return response_data
    except Exception as e:
        # Update agent status to failed in case of error
        update_agent_status(agent_name, "Failed")
        raise e

def add_to_history(role: str, content: str, agent: str = None, session_id: str = None):
    """Add a message to the conversation history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if agent:
        message["agent"] = agent
    
    # Add to global conversation history
    st.session_state.conversation_history.append(message)
    
    # Add to session-specific history if session is provided
    if session_id and session_id in st.session_state.sessions:
        st.session_state.sessions[session_id]["conversation"].append(message)

def get_session_history(session_id: str):
    """Get conversation history for a specific session."""
    if session_id and session_id in st.session_state.sessions:
        return st.session_state.sessions[session_id]["conversation"]
    return []

def display_conversation(session_id: str = None):
    """Display the conversation history in the Streamlit UI."""
    # If session ID is provided, display only that session's conversation
    if session_id and session_id in st.session_state.sessions:
        history = st.session_state.sessions[session_id]["conversation"]
    else:
        history = st.session_state.conversation_history
    
    for message in history:
        if message["role"] == "user":
            st.markdown(f"**You:** {message['content']}")
        else:
            agent_info = f" (via {message.get('agent', 'Unknown Agent')})" if "agent" in message else ""
            st.markdown(f"**Assistant{agent_info}:** {message['content']}")

def display_sessions_dashboard():
    """Display a dashboard of all sessions."""
    st.subheader("Sessions Dashboard")
    
    if not st.session_state.sessions:
        st.info("No sessions created yet. Create a new session to get started.")
        return
    
    # Convert session data to DataFrame for display
    session_data = []
    for session_id, session_info in st.session_state.sessions.items():
        session_data.append({
            "Session ID": session_id[:8] + "...",  # Truncate for display
            "Created": session_info["created_at"],
            "Messages": len(session_info["conversation"]),
            "Last Agent": session_info["last_agent"] or "None",
            "Agents Used": ", ".join(session_info["agents_used"]) if session_info["agents_used"] else "None",
            "Is Current": "Yes" if session_id == st.session_state.current_session_id else "No"
        })
    
    df = pd.DataFrame(session_data)
    
    # Apply styling for current session
    def highlight_current(val):
        if val == "Yes":
            return "background-color: #4CAF50"  # Green
        else:
            return ""
    
    # Display the styled DataFrame
    st.dataframe(df.style.applymap(highlight_current, subset=["Is Current"]))
    
    # Session management
    col1, col2 = st.columns(2)
    
    with col1:
        # Select session dropdown
        session_options = ["Select a session"] + list(st.session_state.sessions.keys())
        selected_session = st.selectbox(
            "Switch to Session", 
            session_options,
            format_func=lambda x: x[:8] + "..." if x != "Select a session" else x
        )
        
        if st.button("Switch Session") and selected_session != "Select a session":
            st.session_state.current_session_id = selected_session
            st.success(f"Switched to session {selected_session[:8]}...")
            st.rerun()
    
    with col2:
        # Delete session option
        session_to_delete = st.selectbox(
            "Delete Session", 
            session_options,
            format_func=lambda x: x[:8] + "..." if x != "Select a session" else x,
            key="delete_session"
        )
        
        if st.button("Delete Session") and session_to_delete != "Select a session":
            if session_to_delete == st.session_state.current_session_id:
                st.session_state.current_session_id = None
            
            del st.session_state.sessions[session_to_delete]
            st.success(f"Deleted session {session_to_delete[:8]}...")
            st.rerun()

def update_agent_status(agent_name: str, status: str):
    """Update the status of an agent."""
    if agent_name in st.session_state.agents:
        st.session_state.agents[agent_name]["status"] = status
        st.session_state.agents[agent_name]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_agent_exploration(agent_name: str, full_exploration: bool):
    """Update the full exploration status of an agent."""
    if agent_name in st.session_state.agents:
        st.session_state.agents[agent_name]["full_exploration"] = full_exploration

def increment_agent_exploration(agent_name: str):
    """Increment the explorations completed counter for an agent."""
    if agent_name in st.session_state.agents:
        st.session_state.agents[agent_name]["explorations_completed"] += 1

def display_agent_dashboard():
    """Display a dashboard of agent statuses."""
    st.subheader("Agent Dashboard")
    
    # Convert agent data to DataFrame for display
    agent_data = []
    for agent_name, agent_info in st.session_state.agents.items():
        agent_data.append({
            "Agent": agent_name,
            "Status": agent_info["status"],
            "Last Active": agent_info["last_active"] or "Never",
            "Explorations": agent_info["explorations_completed"],
            "Full Exploration": "Yes" if agent_info["full_exploration"] else "No"
        })
    
    df = pd.DataFrame(agent_data)
    
    # Apply styling based on status
    def color_status(val):
        if val == "Active":
            return "background-color: #FFEB3B"  # Yellow
        elif val == "Completed":
            return "background-color: #4CAF50"  # Green
        elif val == "Failed":
            return "background-color: #F44336"  # Red
        else:
            return ""
    
    # Apply styling based on full exploration
    def color_exploration(val):
        if val == "Yes":
            return "background-color: #4CAF50"  # Green
        else:
            return ""
    
    # Display the styled DataFrame
    st.dataframe(df.style.applymap(color_status, subset=["Status"])
                      .applymap(color_exploration, subset=["Full Exploration"]))
    
    # Add metrics for quick overview
    col1, col2, col3 = st.columns(3)
    with col1:
        active_agents = sum(1 for agent in st.session_state.agents.values() if agent["status"] == "Active")
        st.metric("Active Agents", active_agents)
    
    with col2:
        total_explorations = sum(agent["explorations_completed"] for agent in st.session_state.agents.values())
        st.metric("Total Explorations", total_explorations)
        
    with col3:
        full_explorations = sum(1 for agent in st.session_state.agents.values() if agent["full_exploration"])
        st.metric("Full Explorations", full_explorations)

def main():
    st.set_page_config(page_title="Multi-Agent Chat Interface", layout="wide")
    
    st.title("Multi-Agent Chat Interface with Dashboard")
    
    # Create tabs for chat, agent dashboard, and sessions
    tab1, tab2, tab3 = st.tabs(["Chat", "Agent Dashboard", "Sessions"])
    
    with tab1:
        # Chat interface
        st.subheader("Chat with LangFlow Agents")
        
        # Session selection/creation
        session_col1, session_col2 = st.columns([3, 1])
        
        with session_col1:
            current_session = "None"
            if st.session_state.current_session_id:
                current_session = f"{st.session_state.current_session_id[:8]}..."
            
            st.info(f"Current Session: {current_session}")
        
        with session_col2:
            if st.button("New Session"):
                with st.spinner("Creating new session..."):
                    session_id = start_new_session()
                    if session_id:
                        st.session_state.current_session_id = session_id
                        st.success(f"Created new session: {session_id[:8]}...")
                        st.rerun()
        
        # Agent selection
        agent_options = list(st.session_state.agents.keys())
        selected_agent = st.selectbox("Select Agent", agent_options)
        
        # Display conversation history for current session
        st.subheader("Conversation")
        display_conversation(st.session_state.current_session_id)
        
        # User input
        message = st.text_area("Message", placeholder="Ask something...")
        
        if st.button("Send"):
            if not message.strip():
                st.error("Please enter a message")
                return
            
            if not st.session_state.current_session_id:
                st.warning("No active session. Creating a new session...")
                session_id = start_new_session()
                if not session_id:
                    st.error("Failed to create a new session. Please try again.")
                    return
                st.session_state.current_session_id = session_id
            
            # Add user message to history
            add_to_history("user", message, session_id=st.session_state.current_session_id)
            
            try:
                with st.spinner(f"Running flow with {selected_agent}..."):
                    # Get session-specific history
                    session_history = get_session_history(st.session_state.current_session_id)
                    
                    # Pass the conversation history to LangFlow with the selected agent
                    response = run_flow(
                        message,
                        agent_name=selected_agent,
                        history=session_history[:-1],  # Exclude the current message
                        session_id=st.session_state.current_session_id
                    )
                    
                    # Extract the response text
                    response_text = response["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                    
                    # Add bot response to history with agent info
                    add_to_history("assistant", response_text, selected_agent, st.session_state.current_session_id)
                    
                    # Force a rerun to update the display
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.error("Response: " + str(response) if 'response' in locals() else "No response received")
                
                # Update agent status to failed
                update_agent_status(selected_agent, "Failed")
        
        # Conversation management options
        col1, col2 = st.columns(2)
        with col1:
            # Add option to clear conversation
            if st.button("Clear Current Conversation"):
                if st.session_state.current_session_id and st.session_state.current_session_id in st.session_state.sessions:
                    st.session_state.sessions[st.session_state.current_session_id]["conversation"] = []
                st.rerun()
                
        with col2:
            # Save conversation as downloadable file
            if st.button("Download Current Conversation"):
                if not st.session_state.current_session_id:
                    st.warning("No active session to download.")
                    return
                    
                # Get the conversation for the current session
                conversation = get_session_history(st.session_state.current_session_id)
                
                # Convert conversation history to JSON string
                json_str = json.dumps(conversation, indent=2)
                
                # Create a download button for the JSON file
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"conversation_{st.session_state.current_session_id[:8]}.json",
                    mime="application/json"
                )
    
    with tab2:
        # Agent dashboard
        display_agent_dashboard()
        
        # Add a section for agent management
        st.subheader("Agent Management")
        
        # Reset agent status
        col1, col2 = st.columns(2)
        with col1:
            agent_to_reset = st.selectbox("Reset Agent Status", 
                                         ["Select an agent"] + agent_options)
            if st.button("Reset Status") and agent_to_reset != "Select an agent":
                update_agent_status(agent_to_reset, "Idle")
                st.success(f"Reset {agent_to_reset} status to Idle")
                st.rerun()
                
        with col2:
            if st.button("Reset All Agents"):
                for agent in st.session_state.agents:
                    st.session_state.agents[agent]["status"] = "Idle"
                    st.session_state.agents[agent]["full_exploration"] = False
                st.success("All agents reset to Idle status")
                st.rerun()
        
        # Add a new agent
        st.subheader("Add New Agent")
        new_agent_name = st.text_input("New Agent Name")
        if st.button("Add Agent") and new_agent_name:
            if new_agent_name not in st.session_state.agents:
                st.session_state.agents[new_agent_name] = {
                    "status": "Idle", 
                    "last_active": None, 
                    "explorations_completed": 0, 
                    "full_exploration": False
                }
                st.success(f"Added new agent: {new_agent_name}")
                st.rerun()
            else:
                st.error(f"Agent {new_agent_name} already exists")
    
    with tab3:
        # Sessions dashboard
        display_sessions_dashboard()
        
        # Session statistics
        if st.session_state.sessions:
            st.subheader("Session Statistics")
            
            # Total sessions
            total_sessions = len(st.session_state.sessions)
            total_messages = sum(len(s["conversation"]) for s in st.session_state.sessions.values())
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sessions", total_sessions)
            with col2:
                st.metric("Total Messages", total_messages)
            with col3:
                avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
                st.metric("Avg. Messages per Session", f"{avg_messages:.1f}")
            
            # Auto-refresh dashboard option
            if st.checkbox("Auto-refresh sessions (every 10 seconds)"):
                st.write("Sessions will refresh automatically...")
                time.sleep(10)
                st.rerun()

if __name__ == "__main__":
    main()