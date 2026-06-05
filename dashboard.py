import streamlit as st
import requests
import base64

# 1. Configure the Web Page
st.set_page_config(page_title="VitalPulse AI", page_icon="🏥", layout="centered")

# --- CUSTOM SHAPED HEADER (Gentle Crescent Arc) ---
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

img_base64 = get_image_as_base64("hospital_bg.jpg")

if img_base64:
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: -10px;">
            <div style="
                width: 70%; 
                height: 220px; 
                background-image: url('data:image/jpeg;base64,{img_base64}');
                background-size: cover;
                background-position: center;
                border-bottom-left-radius: 50% 25%;
                border-bottom-right-radius: 50% 25%;
                box-shadow: 0px 8px 20px rgba(0,0,0,0.1);
            "></div>
            <div style='text-align: center; font-size: 12px; margin-top: 12px;'>
                <a href='https://www.magnific.com/free-vector/hospital-clinic-building-with-ambulance-car-truck_8792283.htm' target='_blank' style='color: gray; text-decoration: none;'>
                    Image Source: Magnific
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
# --------------------------------------------------

# --- CENTERED TITLES ---
st.markdown("<h1 style='text-align: center;'>🏥 VitalPulse Command Center</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Interact with the live clinical Lakehouse via the Gemini RAG endpoint.</p>", unsafe_allow_html=True)

# --- SIDEBAR: PORTFOLIO & ARCHITECTURE ---
with st.sidebar:
    st.header("👨‍💻 About the Developer")
    st.markdown("**Harshith Bharathbhushan**")
    st.markdown("Data & Analytics Engineer | May 2026 Grad")
    
    # Don't forget to put your real links here!
    st.markdown("[🔗 View Source on GitHub](https://github.com/harshithbhushan/the-vital-pulse)")
    st.markdown("[🔗 Connect on LinkedIn](https://www.linkedin.com/in/harshithbhushan/)")
    
    st.divider()
    
    st.header("🛠️ Medallion Architecture")
    st.markdown(
        """
        This dashboard serves the **Gold Layer** of a real-time clinical Lakehouse.
        
        **The Pipeline:**
        * **Bronze:** Redpanda (Kafka) live stream
        * **Silver:** PySpark & Apache Iceberg
        * **Gold:** Qdrant Vector Database
        * **Serving:** FastAPI RAG Endpoint
        * **Inference:** Gemini Flash LLM
        """
    )
# -----------------------------------------

# 2. Initialize the Chat History (Memory)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If the AI provided sources, display them in an expandable box
        if "sources" in message and message["sources"]:
            with st.expander("🔍 View Retrieved Patient Records"):
                for idx, source in enumerate(message["sources"]):
                    st.caption(f"{idx + 1}. {source}")

# 4. The Chat Input Bar
if prompt := st.chat_input("Ask about the clinical anomalies (e.g., 'Did the patient experience Hypoxemia?')..."):
    
    # Immediately display the user's question on the screen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 5. Call the FastAPI Backend
    with st.chat_message("assistant"):
        with st.spinner("🧠 Querying Qdrant and Gemini..."):
            try:
                # Send the question to our local API bridge
                response = requests.post(
                    "http://127.0.0.1:8000/ask",
                    json={"question": prompt}
                )
                
                # If the API succeeds, parse the JSON response
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data.get("sources_used", [])

                    # Display the AI's answer
                    st.markdown(answer)
                    
                    # Display the evidence
                    if sources:
                        with st.expander("🔍 View Retrieved Patient Records"):
                            for idx, source in enumerate(sources):
                                st.caption(f"{idx + 1}. {source}")

                    # Save the AI's response to memory
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error(f"API Error {response.status_code}: Something broke in the backend.")
            
            except requests.exceptions.ConnectionError:
                st.error("🚨 Connection Error: Is your FastAPI server (uvicorn) running in the background?")