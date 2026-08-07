FROM python:3.12-slim

WORKDIR /app

# Dépendances d'abord (cache des couches), puis le code.
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
RUN pip install --no-cache-dir ".[app,docs]"

COPY app ./app

# Dossier de travail surveillé (monté en volume en pratique).
ENV FAST2MD_ROOT=/app/FAST2MD
RUN mkdir -p /app/FAST2MD/Inbox /app/FAST2MD/Markdown

EXPOSE 8501

# Service web par défaut ; le watcher est lancé via docker-compose (autre commande).
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]
