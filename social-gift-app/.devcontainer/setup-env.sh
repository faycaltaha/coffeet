#!/bin/bash
# Crée .env.local depuis les secrets Codespaces injectés en variables d'environnement

ENV_FILE=".env.local"

echo "# Généré automatiquement par Codespaces — ne pas commiter" > "$ENV_FILE"

if [ -n "$OPENROUTER_API_KEY" ]; then
  echo "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" >> "$ENV_FILE"
  echo "✅ OPENROUTER_API_KEY injectée dans $ENV_FILE"
else
  echo "⚠️  OPENROUTER_API_KEY non trouvée — ajoute-la dans Settings > Secrets > Codespaces"
fi
