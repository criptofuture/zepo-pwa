#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Zepo PWA — Deploy script (v2 — physical /pwa/ structure)
#
# CRITICAL CONTEXT (no olvidar):
# - CF Pages SOLO aplica _headers a archivos que existen FISICAMENTE
# - Si usas _redirects rewrites, CF pone su cache default (7 dias!)
# - Solucion: archivos viven en _dist/pwa/ fisicamente, no en rewrites
#
# Uso:
#   ./deploy.sh preview      → deploy preview (Zepo Dev)
#   ./deploy.sh promote      → promover preview a produccion
#   ./deploy.sh prod         → deploy directo a produccion
#   ./deploy.sh status       → ver ultimos deploys
# ═══════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

PROJECT="zepo"
PROD_BRANCH="main"
PREVIEW_BRANCH="dev"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# --- Build dist directory with proper /pwa/ structure ---
build_dist() {
  local manifest_src="$1"  # "prod" or "dev"
  echo "  Building _dist/ with physical /pwa/ structure..."
  rm -rf _dist
  mkdir -p _dist/pwa/icons

  # Copy app files into /pwa/
  cp index.html sw.js _dist/pwa/
  if [ "$manifest_src" = "dev" ]; then
    cp manifest-dev.json _dist/pwa/manifest.json
  else
    cp manifest.json _dist/pwa/manifest.json
  fi

  # Copy icons (exclude .bak and .py)
  for f in icons/*; do
    case "$f" in
      *.bak|*.py) ;;
      *) cp "$f" _dist/pwa/icons/ ;;
    esac
  done

  # Copy reset.html at root (outside /pwa/ so it's outside SW scope)
  cp reset.html _dist/

  # Write _headers with rules for physical paths under /pwa/
  cat > _dist/_headers <<'EOF'
# Critical: SW and HTML must never be cached
# Paths exist PHYSICALLY under /pwa/, so headers apply

/pwa/sw-v54.js
  Cache-Control: no-cache, no-store, must-revalidate
  Service-Worker-Allowed: /

/pwa/index.html
  Cache-Control: no-cache, no-store, must-revalidate

/pwa/
  Cache-Control: no-cache, no-store, must-revalidate

/pwa/manifest.json
  Cache-Control: no-cache, no-store, must-revalidate

/reset.html
  Cache-Control: no-cache, no-store, must-revalidate

/pwa/icons/*
  Cache-Control: public, max-age=3600
EOF

  # _redirects: only root → /pwa/
  cat > _dist/_redirects <<'EOF'
/ /pwa/ 302
EOF

  echo "  ✓ _dist/ ready"
}

cleanup_dist() {
  # Keep _dist for inspection but it's gitignored
  echo "  (_dist/ left for inspection)"
}

case "${1:-help}" in

  preview|test|dev)
    echo -e "${CYAN}${BOLD}═══ Zepo Preview Deploy ═══${NC}"
    echo ""
    build_dist dev
    echo ""
    echo "Subiendo preview..."
    cd _dist
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PREVIEW_BRANCH" \
      --commit-dirty=true
    cd ..
    echo ""
    echo -e "${GREEN}${BOLD}Preview deployado.${NC}"
    echo ""
    echo -e "  ${BOLD}URL:${NC} https://dev.zepo-bca.pages.dev/pwa/"
    echo -e "  ${BOLD}Reset:${NC} https://dev.zepo-bca.pages.dev/reset"
    echo ""
    echo -e "  ${YELLOW}Si tenias instalado Zepo Dev antes:${NC}"
    echo -e "  1. Abre primero la URL /reset → limpia SW viejo"
    echo -e "  2. Click 'Abrir Zepo' → te lleva al app"
    echo -e "  3. Instala desde el menu del browser"
    ;;

  promote)
    echo -e "${CYAN}${BOLD}═══ Promover Preview a Produccion ═══${NC}"
    echo ""
    read -p "Ya probaste en Zepo Dev? (s/N) " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
      echo "Cancelado."
      exit 0
    fi
    build_dist prod
    echo ""
    echo "Subiendo a produccion..."
    cd _dist
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PROD_BRANCH" \
      --commit-dirty=true
    cd ..
    echo ""
    echo -e "${GREEN}${BOLD}Produccion actualizada.${NC}"
    echo -e "  https://app.zepo.lynoia.com/pwa/"
    echo -e "  Reset: https://app.zepo.lynoia.com/reset"
    ;;

  prod|production)
    echo -e "${CYAN}${BOLD}═══ Zepo Production Deploy (directo) ═══${NC}"
    echo -e "${YELLOW}Salta el preview.${NC}"
    echo ""
    read -p "Confirmar? (s/N) " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
      echo "Cancelado."
      exit 0
    fi
    build_dist prod
    cd _dist
    npx wrangler@latest pages deploy . \
      --project-name="$PROJECT" \
      --branch="$PROD_BRANCH" \
      --commit-dirty=true
    cd ..
    echo ""
    echo -e "${GREEN}${BOLD}Produccion actualizada.${NC}"
    echo -e "  https://app.zepo.lynoia.com/pwa/"
    ;;

  status|list)
    npx wrangler@latest pages deployment list --project-name="$PROJECT" 2>&1 | head -20
    ;;

  *)
    echo -e "${BOLD}Zepo PWA Deploy v2${NC}"
    echo ""
    echo "Comandos:"
    echo -e "  ${CYAN}preview${NC}   Deploy a Zepo Dev"
    echo -e "  ${CYAN}promote${NC}   Preview → produccion"
    echo -e "  ${CYAN}prod${NC}      Deploy directo a produccion"
    echo -e "  ${CYAN}status${NC}    Ver ultimos deploys"
    echo ""
    echo "URLs:"
    echo "  Produccion: https://app.zepo.lynoia.com/pwa/"
    echo "  Preview:    https://dev.zepo-bca.pages.dev/pwa/"
    echo "  Reset:      https://app.zepo.lynoia.com/reset  (limpia SW viejo)"
    ;;
esac
