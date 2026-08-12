#!/usr/bin/env bash
set -euo pipefail
mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)
source .env
pg_dump "$DATABASE_URL" > "backups/opensight-$stamp.sql"
tar -czf "backups/opensight-data-$stamp.tar.gz" data/media data/clips data/thumbnails
printf 'Backup created: %s\n' "$stamp"
