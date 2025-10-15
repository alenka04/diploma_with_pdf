# main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_engine import prepare_pdf_and_qdrant, generate_answer_with_rag, llm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from qdrant_client.http import models
from rag_engine import encode_texts, extract_keywords

app = FastAPI()

# Разрешение CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #пока так, потом заменю на ["http://localhost:8080"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Путь к PDF
PDF_PATH = r"D:\app_rag\приём.pdf"

# Инициализируем клиент Qdrant и загружаем PDF один раз при старте
qdrant_client = prepare_pdf_and_qdrant(PDF_PATH)

class QuestionRequest(BaseModel):
    question: str

class ChunkUpdateRequest(BaseModel):
    action: str  # "add", "update", "delete"
    id: int = None
    text: str = None
    keywords: list = []

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    try:
        answer = generate_answer_with_rag(request.question, qdrant_client, llm)
        return {"answer": answer}
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/sync_chunk")
async def sync_chunk(request: ChunkUpdateRequest):
    try:
        if request.action == "delete":
            if request.id is None:
                raise HTTPException(status_code=400, detail="ID обязателен для удаления")
            # Удаляем из Qdrant по ID
            qdrant_client.delete(
                collection_name="admission_chunks",
                points_selector=models.PointIdsList(points=[request.id])
            )
            return {"status": "deleted", "id": request.id}

        elif request.action in ["add", "update"]:
            if not request.text:
                raise HTTPException(status_code=400, detail="Текст обязателен")
            if request.id is None and request.action == "add":
                raise HTTPException(status_code=400, detail="ID обязателен для добавления")

            # Генерируем эмбеддинг
            vector = encode_texts([request.text])[0]

            payload = {
                "text": request.text,
                "keywords": request.keywords or []
            }

            # Добавляем или обновляем
            qdrant_client.upsert(
                collection_name="admission_chunks",
                points=[
                    models.PointStruct(id=request.id or 999999, vector=vector.tolist(), payload=payload)
                ]
            )
            return {"status": "upserted", "id": request.id}

        else:
            raise HTTPException(status_code=400, detail="Неверное действие")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Раздаём статические файлы из папки front
app.mount("/static", StaticFiles(directory="front"), name="static")

@app.get("/")
def read_index():
    return FileResponse("front/index.html")