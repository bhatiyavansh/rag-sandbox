
# from fastapi import FastAPI
# from dotenv import load_dotenv
# import os
# from client import generate_api_response

# load_dotenv()

# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# app = FastAPI(title="RAG Playground 🚀")

# # Dummy documents / context for testing
# docs = [
#     "Python is a programming language.",
#     "FastAPI is a Python framework for building APIs.",
#     "LangChain helps you build RAG applications."
# ]

# def ask_question(query: str) -> str:
#     """
#     Retrieves context from documents and queries DeepSeek API.
#     """
#     # For now, just join all docs as context
#     context = "\n".join(docs)
#     return generate_api_response(context, query)

# @app.get("/")
# def home():
#     return {"message": "RAG Playground running 🚀"}

# @app.get("/ask")
# def ask(q: str):
#     answer = ask_question(q)
#     return {"question": q, "answer": answer}


# main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

load_dotenv()

from client import generate_api_response
from content import generate_subtopic_items
# from client import generate_full_learning_json  # adjust import path if required

app = FastAPI(title="RAG Roadmap API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allow only your local frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # adjust as needed
    allow_headers=["*"],
)

# Pydantic models for response docs
class SubtopicModel(BaseModel):
    type: str
    name: str

class TopicModel(BaseModel):
    type: str
    name: str
    subtopics: List[SubtopicModel]



@app.get("/")
def home():
    return {"message": "RAG Roadmap running"}

@app.get("/ask", response_model=List[TopicModel])
def ask(q: str = Query(..., description="Subject to generate roadmap for")):
    """
    Returns an array of Topic objects for the requested subject.
    """
    # You can include ctx from files/repo if available, currently empty string used
    context = ""
    result = generate_api_response(context, q)
    # result=generate_subtopic_items(context, q)
    # result is already a list of dicts validated & repaired by client
    return result

# ------------------ content.py ------------------
@app.get("/content")
def ask(q: str = Query(..., description="Subject to generate roadmap for")):
    """
    Returns an array of Topic objects for the requested subject.
    """
    # You can include ctx from files/repo if available, currently empty string used
    context = ""
    # result = generate_api_response(context, q)
    result=generate_subtopic_items(context, q)
    # result is already a list of dicts validated & repaired by client
    return result