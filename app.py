import streamlit as st
import pandas as pd
import requests
import os
from google import genai
from dotenv import load_dotenv

# Load local environment variables (for local dev only)
load_dotenv()

# --- 1. SECURE CONFIGURATION ---
# Checks Streamlit Cloud Secrets first, then falls back to local .env
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
MONDAY_API_KEY = st.secrets.get("MONDAY_API_KEY") or os.getenv("MONDAY_API_KEY")

# Replace these with your actual Monday.com Board IDs
DEALS_BOARD_ID = "5027110359" 
WORK_BOARD_ID = "5027110768"

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. DATA FETCHING & RESILIENCE ---
def fetch_monday_data(board_id):
    """Fetches data from Monday.com and cleans it for the AI."""
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": MONDAY_API_KEY,
        "API-Version": "2023-10"
    }
    query = f"""
    query {{
      boards(ids: {board_id}) {{
        items_page(limit: 100) {{
          items {{
            name
            column_values {{
              text
              column {{ title }}
            }}
          }}
        }}
      }}
    }}
    """
    try:
        response = requests.post(url, json={'query': query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        items = data["data"]["boards"][0]["items_page"]["items"]
        rows = []
        for item in items:
            row = {"Item Name": item.get("name", "Unnamed")}
            for col in item.get("column_values", []):
                title = col.get("column", {}).get("title", "Unknown")
                text = col.get("text", "")
                row[title] = text
            rows.append(row)
        
        # Data Resilience: Normalize messy data and handle nulls
        df = pd.DataFrame(rows)
        return df.fillna("Not Provided").replace(r'^\s*$', "Not Provided", regex=True)
    
    except Exception as e:
        st.error(f"Failed to fetch board {board_id}: {e}")
        return pd.DataFrame()

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Skylark BI Agent", page_icon="📊", layout="wide")
st.title("📊 Founder's Business Intelligence Agent")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for controls
with st.sidebar:
    st.header("Control Panel")
    if st.button("🔄 Sync Live Data"):
        with st.spinner("Accessing Monday.com..."):
            st.session_state.deals_df = fetch_monday_data(DEALS_BOARD_ID)
            st.session_state.work_df = fetch_monday_data(WORK_BOARD_ID)
            st.success("Data Synchronized!")
    
    if st.button("✨ Leadership Summary"):
        st.session_state.messages.append({
            "role": "user", 
            "content": "Provide a high-level leadership update summarizing our pipeline health and execution status."
        })

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask about revenue, bottlenecks, or project health..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. AI LOGIC
    if "deals_df" not in st.session_state or st.session_state.deals_df.empty:
        st.warning("Please Sync Live Data from the sidebar first.")
    else:
        with st.chat_message("assistant"):
            # Context preparation
            context_data = f"""
            DEALS DATA (Pipeline):
            {st.session_state.deals_df.to_csv(index=False)}
            
            WORK ORDERS DATA (Execution):
            {st.session_state.work_df.to_csv(index=False)}
            """
            
            try:
                # Using Gemini 2.5 Flash for speed and high volume
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        "You are a senior BI Analyst reporting to a CEO. Provide concise, strategic insights. Mention data quality caveats if fields are 'Not Provided'.",
                        f"Context:\n{context_data}",
                        f"Question: {prompt}"
                    ]
                )
                
                full_response = response.text
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            except Exception as e:
                st.error(f"AI Error: {e}")