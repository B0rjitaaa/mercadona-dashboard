#!/bin/sh
# Daily backup run by the `backup` service of docker-compose.prod.yml:
# a Postgres dump plus a tarball of the receipt PDFs, keeping the last
# BACKUP_KEEP_DAYS days in ./backups on the host.
set -eu

dir=/backups
keep=${BACKUP_KEEP_DAYS:-14}
stamp=$(date +%Y%m%d-%H%M%S)

pg_dump -h db -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$dir/.db-$stamp.dump"
mv "$dir/.db-$stamp.dump" "$dir/db-$stamp.dump"
tar -C /media -cf "$dir/.media-$stamp.tar" .
mv "$dir/.media-$stamp.tar" "$dir/media-$stamp.tar"

find "$dir" -maxdepth 1 \( -name 'db-*.dump' -o -name 'media-*.tar' \) -mtime +"$keep" -delete

echo "$(date -Iseconds) backup ok: db-$stamp.dump media-$stamp.tar"
