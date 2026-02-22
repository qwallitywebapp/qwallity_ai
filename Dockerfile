# syntax=docker/dockerfile:1

FROM python:3.10-slim-bullseye

WORKDIR /code

# Install only what is actually needed
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build MkDocs static site
RUN mkdocs build -f qwallity_app_doc-pkg/mkdocs.yml
EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "--timeout", "120", "app:app"]
