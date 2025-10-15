from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from chonkie import RecursiveChunker
import pdfplumber
import pytesseract
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_cpp import Llama
import numpy as np
import os


# Эмбеддинг модель
tokenizer_embed = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
model_embed = AutoModel.from_pretrained("cointegrated/rubert-tiny2")

# Llama модель
llm = Llama.from_pretrained(
    repo_id="unsloth/Llama-3.1-8B-Instruct-GGUF",
    filename="Llama-3.1-8B-Instruct-Q4_1.gguf",
    n_ctx=4096
)

print("Максимальный контекст модели:", llm.n_ctx())
print("Текущий контекст:", llm.n_tokens)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Функция mean_pooling
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )

# Кодирование текстов
def encode_texts(texts):
    encoded_input = tokenizer_embed(texts, padding=True, truncation=True, return_tensors='pt', max_length=512)
    with torch.no_grad():
        model_output = model_embed(**encoded_input)
    return mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()

# Извлечение ключевых слов
def extract_keywords(text, top_n=5):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text])
    feature_names = vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.toarray()[0]
    top_keywords = [feature_names[i] for i in tfidf_scores.argsort()[-top_n:][::-1]]
    return top_keywords

# Обработка PDF
def prepare_pdf_and_qdrant(pdf_path):
    if os.path.exists("./qdrant_data") and QdrantClient(path="./qdrant_data").collection_exists("admission_chunks"):
        print("Загружаем существующую базу знаний...")
        return QdrantClient(path="./qdrant_data")

    print("Обрабатываем PDF и создаём новую базу...")

    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            image = page.to_image(resolution=300).original
            text = pytesseract.image_to_string(image, lang='rus')
            all_text += text + "\n"

    chunker = RecursiveChunker()
    chunks = chunker(all_text)
    chunk_texts = [chunk.text for chunk in chunks]

    vectors = encode_texts(chunk_texts)

    client = QdrantClient(path="./qdrant_data")

    if client.collection_exists(collection_name="admission_chunks"):
        client.delete_collection(collection_name="admission_chunks")
    client.create_collection(
        collection_name="admission_chunks",
        vectors_config=models.VectorParams(size=vectors.shape[1], distance=models.Distance.COSINE)
    )

    client.upload_collection(
        collection_name="admission_chunks",
        vectors=vectors,
        payload=[{"text": c, "keywords": extract_keywords(c)} for c in chunk_texts],
        ids=list(range(len(chunks)))
    )
    return client

# Генерация ответа
def generate_answer_with_rag(question, qdrant_client, llm_model):
    query_vector = encode_texts([question])[0]
    hits = qdrant_client.search(
        collection_name="admission_chunks",
        query_vector=query_vector,
        limit=1
    )
    context = hits[0].payload['text'] if hits else ""
    print(context)
    prompt = f"Пожалуйста, ответьте на вопрос на основе следующего контекста:\n\nКонтекст: {context}\n\nВопрос: {question}\nОтвет:"
    
    output = llm_model.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )
    generated_text = output['choices'][0]['message']['content']
    return generated_text