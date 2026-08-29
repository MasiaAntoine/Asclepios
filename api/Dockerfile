FROM python:3.12-slim

# Dépendances système pour matplotlib, reportlab, Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev libpng-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Installer les dépendances Python
# (copie depuis le contexte root du projet)
COPY api/requirements.txt /tmp/api-requirements.txt
RUN pip install --no-cache-dir -r /tmp/api-requirements.txt

# api/main.py est monté via le volume docker-compose (./api:/workspace/api)
# donc le code n'est pas copié dans l'image — pratique pour le rechargement à chaud.
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
