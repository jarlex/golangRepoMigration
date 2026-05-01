#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HEADER='bb_repo,gh_repo,module_old,module_new,next_tag,status,notes'

CSV_PATH=""
BASE_DIR=""
STOP_ON_ERROR="true"
HAD_ERROR="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/push_repos.sh --csv <path> --base-dir <dir> [--stop-on-error <true|false>]

Required:
  --csv <path>         CSV de migración (header exacto esperado)
  --base-dir <dir>     Directorio base con repos en <base-dir>/<org>/<repo>

Optional:
  --stop-on-error <v>  true (default) para fail-fast, false para continuar
  --help               Muestra esta ayuda
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

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --csv)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PUSH_MISSING_ARG|message=csv_value_required|row=0|repo=-' >&2
          exit 2
        fi
        CSV_PATH="$2"
        shift 2
        ;;
      --base-dir)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PUSH_MISSING_ARG|message=base_dir_value_required|row=0|repo=-' >&2
          exit 2
        fi
        BASE_DIR="$2"
        shift 2
        ;;
      --stop-on-error)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          printf '%s\n' 'ERR_PUSH_MISSING_ARG|message=stop_on_error_value_required|row=0|repo=-' >&2
          exit 2
        fi
        STOP_ON_ERROR="$2"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        printf 'ERR_PUSH_INVALID_ARG|message=unknown_argument_%s|row=0|repo=-\n' "$1" >&2
        usage >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$CSV_PATH" ]]; then
    printf '%s\n' 'ERR_PUSH_MISSING_ARG|message=csv_required|row=0|repo=-' >&2
    exit 2
  fi
  if [[ -z "$BASE_DIR" ]]; then
    printf '%s\n' 'ERR_PUSH_MISSING_ARG|message=base_dir_required|row=0|repo=-' >&2
    exit 2
  fi
  if [[ ! -f "$CSV_PATH" ]]; then
    printf 'ERR_PUSH_CSV_NOT_FOUND|message=csv_not_found_%s|row=0|repo=-\n' "$CSV_PATH" >&2
    exit 2
  fi
  if [[ "$STOP_ON_ERROR" != "true" && "$STOP_ON_ERROR" != "false" ]]; then
    printf 'ERR_PUSH_INVALID_ARG|message=stop_on_error_must_be_true_or_false|row=0|repo=-\n' >&2
    exit 2
  fi
}

handle_row_error() {
  local code="$1"
  local message="$2"
  local row="$3"
  local repo="$4"

  emit_error "$code" "$message" "$row" "$repo"
  HAD_ERROR="true"

  if [[ "$STOP_ON_ERROR" == "true" ]]; then
    exit 1
  fi
}

has_pending_push_commits() {
  local repo_path="$1"
  local branch="$2"
  local upstream="$3"

  local ahead_count
  ahead_count="$(git -C "$repo_path" rev-list --count "${upstream}..${branch}")"
  [[ "$ahead_count" -gt 0 ]]
}

main() {
  parse_args "$@"

  local header
  IFS= read -r header < "$CSV_PATH" || header=""
  header="${header%$'\r'}"
  if [[ "$header" != "$EXPECTED_HEADER" ]]; then
    printf '%s\n' 'ERR_CSV_HEADER_MISMATCH|message=invalid_csv_header|row=1|repo=-' >&2
    exit 1
  fi

  local line_no=1
  local total_rows=0
  local pushed_branches=0
  local pushed_tags=0

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
      handle_row_error "ERR_CSV_INVALID_GH_REPO" "invalid_gh_repo" "$line_no" "$(trim "$gh_repo")"
      continue
    fi

    local org="${parsed%%/*}"
    local repo="${parsed##*/}"
    local repo_id="$org/$repo"
    local repo_path="${BASE_DIR%/}/$org/$repo"

    if [[ ! -d "$repo_path/.git" ]]; then
      handle_row_error "ERR_PUSH_REPO_NOT_FOUND" "local_repo_not_found" "$line_no" "$repo_id"
      continue
    fi

    local branch
    if ! branch="$(git -C "$repo_path" symbolic-ref --short HEAD 2>/dev/null)"; then
      handle_row_error "ERR_PUSH_NO_CURRENT_BRANCH" "detached_or_invalid_head" "$line_no" "$repo_id"
      continue
    fi

    local upstream
    if ! upstream="$(git -C "$repo_path" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
      handle_row_error "ERR_PUSH_NO_UPSTREAM" "missing_upstream_for_branch" "$line_no" "$repo_id"
      continue
    fi

    if has_pending_push_commits "$repo_path" "$branch" "$upstream"; then
      log_info "row=$line_no repo=$repo_id action=push_branch branch=$branch upstream=$upstream"
      if ! git -C "$repo_path" push; then
        handle_row_error "ERR_PUSH_BRANCH_FAILED" "git_push_branch_failed" "$line_no" "$repo_id"
        continue
      fi
      pushed_branches=$((pushed_branches + 1))
    else
      log_info "row=$line_no repo=$repo_id action=skip_branch_push reason=no_pending_commits"
    fi

    local clean_tag
    clean_tag="$(trim "$next_tag")"
    clean_tag="${clean_tag%$'\r'}"

    if [[ -n "$clean_tag" ]]; then
      if git -C "$repo_path" rev-parse -q --verify "refs/tags/$clean_tag" >/dev/null; then
        log_info "row=$line_no repo=$repo_id action=push_tag tag=$clean_tag"
        if ! git -C "$repo_path" push origin "$clean_tag"; then
          handle_row_error "ERR_PUSH_TAG_FAILED" "git_push_tag_failed" "$line_no" "$repo_id"
          continue
        fi
        pushed_tags=$((pushed_tags + 1))
      else
        log_info "row=$line_no repo=$repo_id action=skip_tag_push tag=$clean_tag reason=tag_not_local"
      fi
    fi
  done

  exec 3<&-

  log_info "summary total_rows=$total_rows pushed_branches=$pushed_branches pushed_tags=$pushed_tags stop_on_error=$STOP_ON_ERROR"

  if [[ "$HAD_ERROR" == "true" ]]; then
    exit 1
  fi
}

main "$@"
