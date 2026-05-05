from google import genai
from dotenv import load_dotenv

# Load your API Key
load_dotenv()
client = genai.Client()

print("🔍 Scanning your API Key for available models...")
for m in client.models.list():
    # We only care about text-generation models
    if "generateContent" in m.supported_actions:
        print(f"✅ {m.name}")