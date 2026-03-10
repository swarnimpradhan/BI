import streamlit as st
import pandas as pd
import requests
import os
from google import genai  # Use the new GenAI SDK
from dotenv import load_dotenv

load_dotenv()

# 1. Initialize Gemini Client
# The SDK automatically looks for the GEMINI_API_KEY environment variable.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Configuration - Replace with your actual Board IDs
DEALS_BOARD_ID = "5027110359"
WORK_BOARD_ID = "5027110768"

def fetch_monday_data(board_id):
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": os.getenv("MONDAY_API_KEY"),
        "API-Version": "2023-10"
    }
    query = f"""
    query {{
      boards(ids: {board_id}) {{
        items_page {{
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
        res = requests.post(url, json={'query': query}, headers=headers).json()
        items = res["data"]["boards"][0]["items_page"]["items"]
        rows = []
        for item in items:
            row = {"Item Name": item["name"]}
            for col in item["column_values"]:
                row[col["column"]["title"]] = col["text"]
            rows.append(row)
        # Data Resilience: Normalize and fill missing values
        return pd.DataFrame(rows).fillna("Not Provided")
    except Exception as e:
        st.error(f"Error fetching board {board_id}: {e}")
        return pd.DataFrame()

# Streamlit Page Config
st.set_page_config(page_title="Skylark BI Agent", layout="wide")
st.title("📊 Founder's BI Agent (Gemini Powered)")

# Sidebar for Setup & Quick Actions
with st.sidebar:
    st.header("Data Management")
    if st.button("Sync Monday.com Data"):
        with st.spinner("Fetching live data..."):
            st.session_state.deals = fetch_monday_data(DEALS_BOARD_ID)
            st.session_state.work = fetch_monday_data(WORK_BOARD_ID)
            st.success("Data Synchronized!")

    if st.button("✨ Generate Leadership Update"):
        if "deals" in st.session_state:
            st.session_state.messages.append({"role": "user", "content": "Give me a high-level summary for leadership."})
        else:
            st.warning("Sync data first!")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Ask about revenue, pipeline, or project status..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if "deals" not in st.session_state:
        st.warning("Please sync data from the sidebar first.")
    else:
        with st.chat_message("assistant"):
            # Prepare context for Gemini
            data_context = f"""
            DEALS DATA:
            {st.session_state.deals.to_csv(index=False)}
            
            WORK ORDERS:
            {st.session_state.work.to_csv(index=False)}
            """
            
            try:
                # Using Gemini 2.5 Flash (high volume, low latency, free tier)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        "You are a BI Analyst. Provide concise insights for a CEO. Mention data quality issues like 'Not Provided'.",
                        f"Context:\n{data_context}",
                        f"Question: {prompt}"
                    ]
                )
                answer = response.text
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"AI Service Error: {e}")