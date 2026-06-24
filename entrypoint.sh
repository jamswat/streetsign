#!/bin/sh
set -e

mkdir -p /data /app/streetsign_server/static/user_files
chown -R streetsign:streetsign /data /app/streetsign_server/static/user_files

if [ ! -f "$DATABASE_FILE" ]; then
    echo "streetsign: no database at $DATABASE_FILE — seeding defaults."
    su-exec streetsign python -c "import db; db.make()"
fi

echo "streetsign: running migrations."
su-exec streetsign python -c "import db; db.run_migrations()"

exec su-exec streetsign python ./run.py waitress
