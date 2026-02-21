FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr build-essential curl && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false

# Copy ONLY dependency files first to leverage Docker cache
COPY services/ai_brain/pyproject.toml services/ai_brain/poetry.lock* /app/ai_brain/
WORKDIR /app/ai_brain
RUN poetry install --no-interaction --no-root --no-directory

# Ensure google-genai is installed (workaround for poetry issues)
RUN pip install google-genai

# Copy shared models
COPY shared /app/shared

# Copy the rest of the source code
COPY services/ai_brain /app/ai_brain

RUN mkdir -p /data

# Set environment variables
ENV SENTENCE_TRANSFORMERS_HOME=/app/models/sentence_transformers
ENV TRANSFORMERS_CACHE=/app/models/transformers_cache
ENV HF_HOME=/app/models/huggingface_cache
ENV TESSDATA_PREFIX=/app/models/tesseract
ENV PYTHONPATH=/app

CMD ["uvicorn", "ai_brain.main:app", "--host", "0.0.0.0", "--port", "9004"]
