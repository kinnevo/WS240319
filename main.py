import requests
import streamlit as st
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# LangFlow connection settings
BASE_API_URL = "http://34.59.108.214:7860/"
FLOW_ID = "840c44d6-52c2-4371-ac95-356dd8703e06"
APPLICATION_TOKEN = os.environ.get("OPENAI_API_KEY")
ENDPOINT = "840c44d6-52c2-4371-ac95-356dd8703e06"  # The endpoint name of the flow

# Initialize session state for conversation memory
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

def run_flow(message: str, history: list = None) -> dict:
    """
    Run the LangFlow with the given message and conversation history.
    
    Args:
        message: The current user message
        history: Optional list of previous conversation messages
    
    Returns:
        The response from LangFlow
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{ENDPOINT}"
    
    # Include conversation history if available
    if history and len(history) > 0:
        # Format history in the way LangFlow expects it
        formatted_history = json.dumps(history)
        
        payload = {
            "input_value": message,
            "output_type": "chat",
            "input_type": "chat",
            "conversation_history": formatted_history
        }
    else:
        payload = {
            "input_value": message,
            "output_type": "chat",
            "input_type": "chat"
        }

    headers = {"Authorization": f"Bearer {APPLICATION_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(api_url, json=payload, headers=headers)
    return response.json()

def add_to_history(role: str, content: str):
    """Add a message to the conversation history."""
    st.session_state.conversation_history.append({
        "role": role,
        "content": content
    })

def display_conversation():
    """Display the conversation history in the Streamlit UI."""
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            st.markdown(f"**You:** {message['content']}")
        else:
            st.markdown(f"**Assistant:** {message['content']}")

def main():
    st.title("Chat Interface with Memory")
    
    # Display conversation history
    display_conversation()
    
    # User input
    message = st.text_area("Message", placeholder="Ask something...")
    
    if st.button("Send"):
        if not message.strip():
            st.error("Please enter a message")
            return
        
        # Add user message to history
        add_to_history("user", message)
        
        try:
            with st.spinner("Running flow..."):
                # Pass the conversation history to LangFlow
                response = run_flow(
                    message, 
                    history=st.session_state.conversation_history[:-1]  # Exclude the current message
                )
                
                # Extract the response text
                response_text = response["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                
                # Add bot response to history
                add_to_history("assistant", response_text)
                
                # Force a rerun to update the display
                st.rerun()
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.error("Response: " + str(response) if 'response' in locals() else "No response received")
    
    # Add option to clear conversation
    if st.button("Clear Conversation"):
        st.session_state.conversation_history = []
        st.rerun()

    # Optional: Save conversation to file
    if st.button("Save Conversation"):
        with open("conversation.json", "w") as f:
            json.dump(st.session_state.conversation_history, f, indent=2)
        st.success("Conversation saved to conversation.json")

if __name__ == "__main__":
    main()