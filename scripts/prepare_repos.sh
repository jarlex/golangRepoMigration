#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HEADER='bb_repo,gh_repo,module_old,module_new,next_tag,status,notes'

CSV_PATH=""
BASE_DIR=""
GHE_HOST="${GHE_HOST:-}"
CLONE_PROTOCOL="ssh"

usage() {
  cat <<'EOF'
Usage:
  scripts/prepare_repos.sh --csv <path> --base-dir <dir> --ghe-host <host> [--https]

Required:
  --csv <path>        CSV de migración (header exacto esperado)
  --base-dir <dir>    Directorio base para clonar repos en <base-dir>/<org>/<repo>
  --ghe-host <host>   Host de GHE para construir URL de clonación

Optional:
  --https             Usa HTTPS en vez de SSH (default: SSH)
  --help              Muestra esta ayuda

Notes:
  - Por defecto clona vía SSH: git@<host>:<org>/<repo>.git
  - Con --https clona vía HTTPS: https://<host>/<org>/<repo>.git
EOF
}

log_info() {
  printf '%s\n' "[INFO] $*"
}

emit_error() {
  local code="$1"
  local message="$2"
  local row="$3"
  local repo="$4"
  printf '%s|message=%s|row=%s|repo=%s\n' "$code" "$message" "$row" "$repo" >&2
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

parse_org_repo() {
  local raw
  raw="$(trim "$1")"
  raw="${raw%"${raw##*[!$'\r']}"}"
  raw="${raw%.git}"

  if [[ "$raw" =~ ^https?://[^/]+/([^/]+)/([^/]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$raw" =~ ^ssh://git@[^/]+/([^/]+)/([^/]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$raw" =~ ^git@[^:]+:([^/]+)/([^/]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$raw" =~ ^([^/]+)/([^/]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  return 1
}

build_clone_url() {
  local org="$1"
  local repo="$2"

  if [[ "$CLONE_PROTOCOL" == "https" ]]; then
    printf 'https://%s/%s/%s.git\n' "$GHE_HOST" "$org" "$repo"
    return 0
  fi

  printf 'git@%s:%s/%s.git\n' "$GHE_HOST" "$org" "$repo"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --csv)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=csv_value_required|row=0|repo=-' >&2
          exit 2
        fi
        CSV_PATH="$2"
        shift 2
        ;;
      --base-dir)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=base_dir_value_required|row=0|repo=-' >&2
          exit 2
        fi
        BASE_DIR="$2"
        shift 2
        ;;
      --ghe-host)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=ghe_host_value_required|row=0|repo=-' >&2
          exit 2
        fi
        GHE_HOST="$2"
        shift 2
        ;;
      --https)
        CLONE_PROTOCOL="https"
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        printf 'ERR_PREPARE_INVALID_ARG|message=unknown_argument_%s|row=0|repo=-\n' "$1" >&2
        usage >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$CSV_PATH" ]]; then
    printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=csv_required|row=0|repo=-' >&2
    exit 2
  fi
  if [[ -z "$BASE_DIR" ]]; then
    printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=base_dir_required|row=0|repo=-' >&2
    exit 2
  fi
  if [[ -z "$GHE_HOST" ]]; then
    printf '%s\n' 'ERR_PREPARE_MISSING_ARG|message=ghe_host_required|row=0|repo=-' >&2
    exit 2
  fi
  if [[ ! -f "$CSV_PATH" ]]; then
    printf 'ERR_PREPARE_CSV_NOT_FOUND|message=csv_not_found_%s|row=0|repo=-\n' "$CSV_PATH" >&2
    exit 2
  fi
}

main() {
  parse_args "$@"

  mkdir -p "$BASE_DIR"

  local header
  IFS= read -r header < "$CSV_PATH" || header=""
  header="${header%$'\r'}"
  if [[ "$header" != "$EXPECTED_HEADER" ]]; then
    printf '%s\n' 'ERR_CSV_HEADER_MISMATCH|message=invalid_csv_header|row=1|repo=-' >&2
    exit 1
  fi

  local line_no=1
  local total_rows=0
  local cloned_count=0
  local existing_count=0

  exec 3< "$CSV_PATH"
  IFS= read -r _ <&3 || true

  while IFS=',' read -r bb_repo gh_repo module_old module_new next_tag status notes <&3; do
    line_no=$((line_no + 1))

    if [[ -z "${bb_repo}${gh_repo}${module_old}${module_new}${next_tag}${status}${notes}" ]]; then
      continue
    fi

    total_rows=$((total_rows + 1))

    local parsed
    if ! parsed="$(parse_org_repo "$gh_repo")"; then
      emit_error "ERR_CSV_INVALID_GH_REPO" "invalid_gh_repo" "$line_no" "$(trim "$gh_repo")"
      exit 1
    fi

    local org="${parsed%%/*}"
    local repo="${parsed##*/}"
    local local_repo_path="${BASE_DIR%/}/$org/$repo"
    local clone_url
    clone_url="$(build_clone_url "$org" "$repo")"

    if [[ -d "$local_repo_path/.git" ]]; then
      existing_count=$((existing_count + 1))
      log_info "row=$line_no repo=$org/$repo action=skip_existing path=$local_repo_path"
      continue
    fi

    mkdir -p "${BASE_DIR%/}/$org"
    log_info "row=$line_no repo=$org/$repo action=clone url=$clone_url path=$local_repo_path"
    if ! git clone "$clone_url" "$local_repo_path"; then
      emit_error "ERR_PREPARE_CLONE_FAILED" "git_clone_failed" "$line_no" "$org/$repo"
      exit 1
    fi
    cloned_count=$((cloned_count + 1))
  done

  exec 3<&-

  log_info "summary total_rows=$total_rows cloned=$cloned_count existing=$existing_count protocol=$CLONE_PROTOCOL"
}

main "$@"
