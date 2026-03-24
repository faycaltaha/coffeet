---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript Coding Style

- Types explicites sur les exports et props
- Pas de `any` — utilise `unknown` si besoin
- Pas de mutation — retourne de nouveaux objets
- Pas de `console.log` en production
- Gestion d'erreurs avec try/catch, messages clairs
