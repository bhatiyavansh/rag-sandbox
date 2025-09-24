# from fastapi import FastAPI
# from rag_pipeline import ask_question

# app = FastAPI()

# @app.get("/")
# def home():
#     return {"message": "RAG Playground running 🚀"}

# @app.get("/ask")
# def ask(q: str):
#     answer = ask_question(q)
#     return {"question": q, "answer": answer}


# src/api/main.py
from fastapi import FastAPI
from dotenv import load_dotenv
import os
from client import generate_api_response

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

app = FastAPI(title="RAG Playground 🚀")

# Dummy documents / context for testing
docs = [
    "Python is a programming language.",
    "FastAPI is a Python framework for building APIs.",
    "LangChain helps you build RAG applications."
]

def ask_question(query: str) -> str:
    """
    Retrieves context from documents and queries DeepSeek API.
    """
    # For now, just join all docs as context
    context = "\n".join(docs)
    return generate_api_response(context, query)

@app.get("/")
def home():
    return {"message": "RAG Playground running 🚀"}

@app.get("/ask")
def ask(q: str):
    answer = ask_question(q)
    return {"question": q, "answer": answer}
