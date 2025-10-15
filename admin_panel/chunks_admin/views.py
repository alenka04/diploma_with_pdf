from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.http import JsonResponse
from .models import Chunk, UploadedDocument
import os
from docx import Document
from chonkie import RecursiveChunker
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
import tempfile
from django.template.loader import render_to_string

# --- Глобальные переменные для эмбеддингов ---
tokenizer_embed = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
model_embed = AutoModel.from_pretrained("cointegrated/rubert-tiny2")

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9)

def encode_texts(texts):
    encoded_input = tokenizer_embed(texts, padding=True, truncation=True, return_tensors='pt', max_length=512)
    with torch.no_grad():
        model_output = model_embed(**encoded_input)
    return mean_pooling(model_output, encoded_input['attention_mask']).cpu().numpy()

def extract_keywords(text, top_n=5):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text])
    feature_names = vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.toarray()[0]
    return [feature_names[i] for i in tfidf_scores.argsort()[-top_n:][::-1]]

#Извлекает текст из .docx файла
def extract_text_from_docx(docx_path): 
    doc = Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text)
    return "\n".join(full_text)

@staff_member_required
def uploaded_documents_page(request):
    documents = UploadedDocument.objects.all().order_by('-uploaded_at')

    if request.method == "POST" and request.FILES.get("document"):
        uploaded_file = request.FILES["document"]

        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, uploaded_file.name)

        try:
            with open(temp_path, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            text = extract_text_from_docx(temp_path)

            chunker = RecursiveChunker()
            chunks = chunker(text)
            chunk_texts = [chunk.text for chunk in chunks]

            for chunk_text in chunk_texts:
                keywords = extract_keywords(chunk_text)
                Chunk.objects.create(
                    text=chunk_text,
                    keywords=", ".join(keywords)
                )

            UploadedDocument.objects.create(
                file=uploaded_file,
                filename=uploaded_file.name,
                chunk_count=len(chunks)
            )

            os.remove(temp_path)

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                html = render_to_string(
                    "admin/document_table.html",
                    {"documents": UploadedDocument.objects.all().order_by('-uploaded_at')}
                )
                return JsonResponse({"success": True, "html": html})

            return render(request, "admin/uploaded_documents.html", {"documents": documents})

        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)})
            return render(request, "admin/uploaded_documents.html", {
                "documents": documents,
                "error": f"Ошибка обработки: {str(e)}"
            })

    return render(request, "admin/uploaded_documents.html", {"documents": documents})
