#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Zepo PWA — Deploy script
#
# Uso:
#   ./deploy.sh preview      → deploy preview (Zepo Dev app)
#   ./deploy.sh promote      → promover preview a produccion
#   ./deploy.sh prod         → deploy directo a produccion
#   ./deploy.sh status       → ver ultimos deploys
#
# Apps instalables:
#   Produccion : app.zepo.lynoia.com/pwa/     → "Zepo"
#   Preview    : dev.zepo-bca.pages.dev/pwa/  → "Zepo Dev"
# ═══════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

PROJECT="zepo"
PROD_BRANCH="main"
PREVIEW_BRANCH="dev"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# --- Helpers ---

swap_to_dev() {
  # Swap manifest to dev version for preview deploy
  cp manifest.json manifest.json.prod-backup
  cp manifest-dev.json manifest.json
  echo "  (manifest swapped to dev)"
}

restore_prod() {
  # Restore production manifest after preview deploy
  if [ -f manifest.json.prod-backup ]; then
    mv manifest.json.prod-backup manifest.json
    echo "  (manifest restored to prod)"
  fi
}

# Trap to always restore manifest if script is interrupted
trap restore_prod EXIT

# --- Commands ---

case "${1:-help}" in

  preview|test|dev)
    echo -e "${CYAN}${BOLD}═══ Zepo Preview Deploy ═══${NC}"
    echo ""
    swap_to_dev
    echo ""
    echo "Subiendo preview..."
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PREVIEW_BRANCH" \
      --commit-dirty=true
    echo ""
    echo -e "${GREEN}${BOLD}Preview deployado.${NC}"
    echo ""
    echo -e "  ${BOLD}URL:${NC} https://dev.zepo-bca.pages.dev/pwa/"
    echo ""
    echo -e "  ${YELLOW}Para instalar Zepo Dev en tu celular:${NC}"
    echo -e "  1. Abre la URL de arriba en Chrome (Android) o Safari (iOS)"
    echo -e "  2. Menu > Instalar app / Agregar a pantalla de inicio"
    echo -e "  3. Aparecera como 'Zepo Dev' con icono naranja"
    echo ""
    echo -e "  Si funciona bien, corre: ${CYAN}./deploy.sh promote${NC}"
    ;;

  promote)
    echo -e "${CYAN}${BOLD}═══ Promover Preview a Produccion ═══${NC}"
    echo -e "${YELLOW}Esto copia lo que esta en preview a app.zepo.lynoia.com${NC}"
    echo ""
    read -p "Ya probaste en Zepo Dev y funciona? (s/N) " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" && "$confirm" != "si" && "$confirm" != "yes" ]]; then
      echo "Cancelado. Prueba primero con: ./deploy.sh preview"
      exit 0
    fi
    echo ""
    echo "Subiendo a produccion (con manifest de prod)..."
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PROD_BRANCH" \
      --commit-hash="$(git rev-parse HEAD 2>/dev/null || echo '')" \
      --commit-message="$(git log -1 --format=%s 2>/dev/null || echo 'manual deploy')" \
      --commit-dirty=true
    echo ""
    echo -e "${GREEN}${BOLD}Produccion actualizada (${COMMIT}).${NC}"
    echo -e "  https://app.zepo.lynoia.com"
    echo -e "  Cierra y reabre Zepo en tu celular."
    ;;

  prod|production)
    echo -e "${CYAN}${BOLD}═══ Zepo Production Deploy (directo) ═══${NC}"
    echo -e "${RED}${BOLD}ATENCION: Esto salta el paso de preview.${NC}"
    echo -e "${YELLOW}Usa './deploy.sh preview' + './deploy.sh promote' para el flujo seguro.${NC}"
    echo ""
    read -p "Seguro que quieres deploy directo a produccion? (s/N) " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" && "$confirm" != "si" && "$confirm" != "yes" ]]; then
      echo "Cancelado."
      exit 0
    fi
    echo ""
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PROD_BRANCH" \
      --commit-hash="$(git rev-parse HEAD 2>/dev/null || echo '')" \
      --commit-message="$(git log -1 --format=%s 2>/dev/null || echo 'manual deploy')" \
      --commit-dirty=true
    echo ""
    echo -e "${GREEN}${BOLD}Produccion actualizada (${COMMIT}).${NC}"
    echo -e "  https://app.zepo.lynoia.com"
    ;;

  status|list)
    echo -e "${CYAN}${BOLD}═══ Ultimos deploys de Zepo ═══${NC}"
    npx wrangler@latest pages deployment list --project-name="$PROJECT" 2>&1 | head -20
    ;;

  *)
    echo -e "${BOLD}Zepo PWA Deploy${NC}"
    echo ""
    echo "Uso: ./deploy.sh <comando>"
    echo ""
    echo "Comandos:"
    echo -e "  ${CYAN}preview${NC}   Deploy a Zepo Dev (probar antes de produccion)"
    echo -e "  ${CYAN}promote${NC}   Promover preview a produccion"
    echo -e "  ${CYAN}prod${NC}      Deploy directo a produccion (salta preview)"
    echo -e "  ${CYAN}status${NC}    Ver ultimos deploys"
    echo ""
    echo "Flujo recomendado:"
    echo "  1. ./deploy.sh preview   → probar en Zepo Dev"
    echo "  2. ./deploy.sh promote   → publicar en Zepo"
    ;;
esac
