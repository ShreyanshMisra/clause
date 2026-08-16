FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# VECTOR_BACKEND is supplied at runtime (render.yaml / dashboard); the app
# defaults to "local" if unset. Not baked in here so it never masks that.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
