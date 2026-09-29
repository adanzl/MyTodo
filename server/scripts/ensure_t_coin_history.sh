#!/usr/bin/env bash
# 在 server 目录执行：按 t_score_history 克隆 t_coin_history（幂等，仅需 sqlite3）
set -euo pipefail
DB="${1:-data.db}"
if [[ ! -f "$DB" ]]; then
  echo "database not found: $DB" >&2
  exit 1
fi
if sqlite3 "$DB" "SELECT 1 FROM sqlite_master WHERE type='table' AND name='t_coin_history';" | grep -q 1; then
  echo "t_coin_history already exists"
  sqlite3 "$DB" ".schema t_coin_history"
  exit 0
fi
clone_sql() {
  sed 's/t_score_history/t_coin_history/g; s/idx_score/idx_coin/g; s/sqlite_autoindex_t_score/sqlite_autoindex_t_coin/g'
}
sqlite3 "$DB" "SELECT sql FROM sqlite_master WHERE type='table' AND name='t_score_history';" \
  | clone_sql \
  | sqlite3 "$DB"
while IFS= read -r idx_sql; do
  [[ -z "$idx_sql" ]] && continue
  echo "$idx_sql" | clone_sql | sqlite3 "$DB" || true
done < <(sqlite3 "$DB" "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='t_score_history' AND sql IS NOT NULL;")
echo "created t_coin_history:"
sqlite3 "$DB" ".schema t_coin_history"
