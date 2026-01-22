FROM python:3.11-slim
WORKDIR /app

# Install kubectl, ping, and curl for system checks
RUN apt-get update && apt-get install -y \
    curl \
    iputils-ping \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root
COPY . .
# copy wait-for script included in repository
COPY wait-for.sh /app/wait-for.sh
RUN chmod +x /app/wait-for.sh
# Start gateway after ai_brain and reminder are healthy
CMD ["/app/wait-for.sh", "ai_brain:9004", "reminder:9002", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
