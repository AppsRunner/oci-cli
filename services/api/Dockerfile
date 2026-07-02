FROM python:3.11-slim

WORKDIR /app

# Install packages/rag first (it's a local dep)
COPY packages/rag /app/packages/rag
RUN pip install --no-cache-dir /app/packages/rag

# Install API service
COPY services/api /app/services/api
RUN pip install --no-cache-dir /app/services/api

WORKDIR /app/services/api
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
