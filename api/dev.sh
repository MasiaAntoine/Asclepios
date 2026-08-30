#!/bin/bash
# Script de développement pour l'API Asclepios

cd "$(dirname "$0")"

# Vérifier le venv
if [ ! -d "../.venv" ]; then
    echo "❌ Virtual env non trouvé. Exécute d'abord :"
    echo "   cd .. && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activer le venv
source ../.venv/bin/activate

# Vérifier que FastAPI est installé
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI non installé. Installe les dépendances :"
    echo "   pip install -r ../requirements.txt"
    exit 1
fi

echo "🚀 Démarrage de l'API Asclepios..."
echo "📍 http://localhost:8000"
echo ""

# Lancer avec uvicorn en mode reload
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
