FROM python:3.11-slim
RUN mkdir -p /app
WORKDIR /app
COPY services/habits/pyproject.toml .
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
COPY services/habits/ .
RUN mkdir -p /data
RUN apt-get update && rm -rf /var/lib/apt/lists/*
COPY services/habits/wait-for-advanced.py /app/wait-for-advanced.py
COPY services/habits/wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for-advanced.py /app/wait-for.sh || true
CMD ["/app/wait-for.sh"]
