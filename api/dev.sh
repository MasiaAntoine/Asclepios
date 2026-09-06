#!/bin/bash
# Script de développement pour l'API Asclepios

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "❌ Virtual env non trouvé. Exécute d'abord :"
    echo "   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate

if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI non installé. Installe les dépendances :"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Démarrage de l'API Asclepios..."
echo "📍 http://localhost:8001"
echo ""

exec uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
