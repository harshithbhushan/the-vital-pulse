from google import genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
client = genai.Client()

print("🔍 Scanning your API Key for available models...")
for m in client.models.list():
    # Text-generation models only
    if "generateContent" in m.supported_actions:
        print(f"✅ {m.name}")