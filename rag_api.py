import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from google import genai  
from dotenv import load_dotenv

# 1. Loading the hidden API key from the .env file
load_dotenv()

# 2. Initialize the Web API
app = FastAPI(title="VitalPulse Clinical RAG API", description="AI Endpoint for Real-Time Patient Anomalies")

# 3. Connecting to the Vector Database & Loading Local Embedder
print("🧠 Connecting to Qdrant...")
qdrant = QdrantClient("http://localhost:6333")

print("🤖 Loading Embedding Model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# 4. Configure Cloud LLM (Gemini)
client = genai.Client()

# Defining the data structure we expect from the user
class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
def ask_clinical_assistant(request: QueryRequest):
    try:
        # STEP A: Vectorize the Doctor's Question
        query_vector = embedder.encode(request.question).tolist()

        # STEP B: Search Qdrant using the Query API
        search_results = qdrant.query_points(
            collection_name="clinical_anomalies",
            query=query_vector,
            limit=40
        ).points

        if not search_results:
            return {
                "question": request.question,
                "answer": "No relevant clinical anomalies found in the database.",
                "sources_used": []
            }

        # STEP C: Extract the raw clinical text from the Qdrant payloads
        context_blocks = []
        for hit in search_results:
            context_blocks.append(hit.payload['context'])

        compiled_context = "\n".join(context_blocks)

        # STEP D: Construct the "Closed-Book" RAG Prompt for Gemini
        prompt = f"""
        You are an expert clinical AI assistant. Use the following retrieved patient anomaly records to answer the doctor's question. 
        If the answer cannot be found in the records below, simply state "I don't have enough data to answer that." 
        Do not make up patient information.

        --- RETRIEVED MEDICAL RECORDS ---
        {compiled_context}
        ---------------------------------

        Doctor's Question: {request.question}
        """

        # STEP E: Generate the final answer
        response = client.models.generate_content(
            model='gemini-3-flash-preview', # Updated to the standard production model from 'gemini-3-flash-preview'
            contents=prompt
        )

        # Return the answer AND the sources we used
        return {
            "question": request.question,
            "answer": response.text,
            "sources_used": context_blocks
        }

    except Exception as e:
        # Log the actual error for the backend terminal so you can debug
        logging.error(f"Inference pipeline failed: {str(e)}")
        
        # Gracefully degrade the response for the frontend UI
        return {
            "question": request.question,
            "answer": "I am currently unable to process that request. My systems are restricted strictly to analyzing the live ICU telemetry and patient anomaly records provided in the context window. If the issue persists, check the backend API logs.",
            "sources_used": []
        }