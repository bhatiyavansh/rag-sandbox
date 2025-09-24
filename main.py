
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
# from fastapi import FastAPI, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List,Any
from pydantic import BaseModel
from io import BytesIO
import PyPDF2
from pdf import extract_pdf_text, chunk_text
from embeddings import get_embedding
from vectorstore import VectorStore
from pdf import extract_pdf_text, chunk_text    

load_dotenv()

from client import generate_api_response
from content import generate_subtopic_items
from general import generate_general_response   

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
class SubtopicItemModel(BaseModel):
    type: str
    content: str

class SubtopicModel(BaseModel):
    type: str
    name: str

class TopicModel(BaseModel):
    type: str
    name: str
    subtopics: List[SubtopicModel]

class MetadataModel(BaseModel):
    events: List[Any]
    roadmap: List[Any]
    messages: List[Any]

class GeneralRequest(BaseModel):
    metadata: MetadataModel
    query: str




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

@app.post("/general")
def general(request: GeneralRequest):
    """
    Accepts metadata and a query, uses metadata as context,
    returns standardized output from LLM.
    """
    # Flatten metadata as context string
    try:
        import json
        context_str = json.dumps(request.metadata.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid metadata: {e}")

    query = request.query

    try:
        # Call your existing API wrapper (no system prompt)
        result = generate_general_response(context_str, query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {e}")



@app.post("/pdf/topics", response_model=List[TopicModel])
async def pdf_topics(file: UploadFile = File(...), query: str = Form(...)):
    """
    Generate topics and subtopics from uploaded PDF.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        chunks = extract_pdf_text(file.file)
        context = "\n".join(chunks)
        result = generate_api_response(context, query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating topics: {e}")

@app.post("/pdf/subtopic_items", response_model=List[SubtopicItemModel])
async def pdf_subtopic_items(file: UploadFile = File(...), subtopic: str = Form(...)):
    """
    Generate QA/STUDY items for a subtopic from uploaded PDF.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        chunks = extract_pdf_text(file.file)
        context = "\n".join(chunks)
        result = generate_subtopic_items(subtopic, context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating subtopic items: {e}")
    

@app.post("/pdf/topics_embeddings")
async def pdf_topics_embeddings(file: UploadFile = File(...), query: str = Form(...)):
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Extract PDF text and chunk
        text = extract_pdf_text(file.file)
        chunks = chunk_text(text, chunk_size=300)
        if not chunks:
            raise HTTPException(status_code=400, detail="PDF is empty")

        # Generate embeddings safely
        embeddings = []
        for c in chunks:
            try:
                emb = get_embedding(c)
                embeddings.append(emb)
            except Exception as e:
                print(f"Skipping chunk due to embedding error: {e}")

        if not embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate embeddings for PDF")

        # Build vector store
        store = VectorStore(dim=len(embeddings[0]))
        store.add(chunks, embeddings)

        # Embed query and search
        query_embedding = get_embedding(query)
        relevant_chunks = store.search(query_embedding, top_k=5)
        context = "\n".join(relevant_chunks)

        # Call LLM
        result = generate_api_response(context, query)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
