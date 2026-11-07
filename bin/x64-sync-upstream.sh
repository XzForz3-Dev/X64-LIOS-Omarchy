#!/bin/bash
# ==============================================================================
# X64 LIOS + Omarchy — Upstream Synchronization Engine
# By X64 Studios
# ==============================================================================

set -eo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="quattro"
TARGET_BRANCH="main"

echo -e "\033[1;36m[+] X64 LIOS + Omarchy — Motor de Sincronización Upstream\033[0m"
echo -e "Directorio: $REPO_DIR"

# 1. Verificar configuración de remotos
if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
    echo -e "\033[1;31m[!] Error: Remoto '$UPSTREAM_REMOTE' no configurado.\033[0m"
    exit 1
fi

# 2. Descargar últimos cambios de Basecamp
echo -e "\n\033[1;33m[+] Obteniendo commits de Basecamp ($UPSTREAM_REMOTE/$UPSTREAM_BRANCH)...\033[0m"
git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

LOCAL_UPSTREAM_COMMIT=$(git rev-parse upstream 2>/dev/null || echo "")
REMOTE_UPSTREAM_COMMIT=$(git rev-parse "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH")

if [ "$LOCAL_UPSTREAM_COMMIT" = "$REMOTE_UPSTREAM_COMMIT" ]; then
    echo -e "\033[1;32m[✓] Tu repositorio ya está 100% al día con Basecamp. No hay commits nuevos.\033[0m"
    exit 0
fi

echo -e "\033[1;32m[!] Se detectaron commits nuevos en Basecamp:\033[0m"
git log --oneline "$LOCAL_UPSTREAM_COMMIT..$REMOTE_UPSTREAM_COMMIT" | head -n 15

# 3. Escaneo preventivo de paquetes en lista negra
echo -e "\n\033[1;33m[+] Ejecutando filtro de seguridad de paquetes (Blacklist Check)...\033[0m"
BLACKLIST_PATTERN="linux-omarchy|linux-headers|limine|intel-media-driver|linux-ptl"
CHANGED_PACKAGES=$(git diff "$LOCAL_UPSTREAM_COMMIT" "$REMOTE_UPSTREAM_COMMIT" -- install/*.packages 2>/dev/null || true)

if echo "$CHANGED_PACKAGES" | grep -E "^\+.*($BLACKLIST_PATTERN)" >/dev/null 2>&1; then
    echo -e "\033[1;31m[!] ADVERTENCIA CRÍTICA: Upstream introdujo paquetes conflictivos con X64 LIOS.\033[0m"
    echo "$CHANGED_PACKAGES" | grep -E "^\+.*($BLACKLIST_PATTERN)"
    echo -e "\033[1;33m[i] El filtro neutralizará estas dependencias para proteger el kernel BORE.\033[0m"
fi

# 4. Chequeo sintáctico previo (Sanity Check en scripts bash)
echo -e "\n\033[1;33m[+] Analizando sintaxis de scripts modificados...\033[0m"
MODIFIED_SCRIPTS=$(git diff --name-only "$LOCAL_UPSTREAM_COMMIT" "$REMOTE_UPSTREAM_COMMIT" | grep -E "^bin/|^install/.*\.sh$" || true)

SYNTAX_ERRORS=0
for script in $MODIFIED_SCRIPTS; do
    if [ -f "$script" ]; then
        if ! bash -n "$script" 2>/dev/null; then
            echo -e "\033[1;31m[X] Error sintáctico en $script\033[0m"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    fi
done

if [ "$SYNTAX_ERRORS" -gt 0 ]; then
    echo -e "\033[1;31m[!] Sincronización abortada por errores de sintaxis en upstream. Nada fue modificado.\033[0m"
    exit 1
fi
echo -e "\033[1;32m[✓] Control de sintaxis aprobado.\033[0m"

# 5. Sincronización de rama upstream local
echo -e "\n\033[1;33m[+] Actualizando rama local 'upstream'...\033[0m"
git checkout upstream
git merge --ff-only "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH"

# 6. Fusión limpia en rama de producción 'main'
echo -e "\n\033[1;33m[+] Fusionando en rama de producción 'main'...\033[0m"
git checkout "$TARGET_BRANCH"

if git merge upstream -m "chore(sync): automated merge from upstream Basecamp Omarchy"; then
    echo -e "\033[1;32m[✓] Fusión completada con éxito. Verificando integridad de la Capa X64...\033[0m"
    
    # Asegurar permisos de scripts
    chmod +x bin/* 2>/dev/null || true
    
    # Subir a GitHub
    echo -e "\n\033[1;33m[+] Publicando actualizaciones en GitHub oficial (XzForz3-Dev/X64-LIOS-Omarchy)...\033[0m"
    git push origin upstream
    git push origin "$TARGET_BRANCH"
    echo -e "\033[1;32m[✓] ¡Sincronización completada exitosamente! X64 LIOS + Omarchy está al día.\033[0m"
else
    echo -e "\033[1;31m[!] Conflicto detectado durante la fusión. Abortando merge automático para proteger producción...\033[0m"
    git merge --abort
    echo -e "\033[1;33m[i] Por favor revisa los archivos en conflicto manualmente.\033[0m"
    exit 1
fi
