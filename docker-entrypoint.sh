#!/bin/sh
set -eu

should_run_migrations=0
if [ "${RUN_MIGRATIONS_ON_STARTUP:-true}" = "true" ] && [ "${1:-}" = "uvicorn" ]; then
    should_run_migrations=1
fi

run_migrations() {
    attempt=1
    max_attempts="${MIGRATION_MAX_ATTEMPTS:-20}"
    sleep_seconds="${MIGRATION_RETRY_SLEEP_SECONDS:-2}"

    while [ "$attempt" -le "$max_attempts" ]; do
        if alembic upgrade head; then
            return 0
        fi
        echo "Migration attempt ${attempt}/${max_attempts} failed; retrying in ${sleep_seconds}s..."
        attempt=$((attempt + 1))
        sleep "$sleep_seconds"
    done

    echo "Migration failed after ${max_attempts} attempts."
    return 1
}

run_migrations_as_user() {
    run_uid="$1"
    run_gid="$2"
    attempt=1
    max_attempts="${MIGRATION_MAX_ATTEMPTS:-20}"
    sleep_seconds="${MIGRATION_RETRY_SLEEP_SECONDS:-2}"

    while [ "$attempt" -le "$max_attempts" ]; do
        if gosu "$run_uid:$run_gid" sh -c 'cd /app && alembic upgrade head'; then
            return 0
        fi
        echo "Migration attempt ${attempt}/${max_attempts} failed; retrying in ${sleep_seconds}s..."
        attempt=$((attempt + 1))
        sleep "$sleep_seconds"
    done

    echo "Migration failed after ${max_attempts} attempts."
    return 1
}

if [ -d /app ]; then
    cd /app
    app_uid="$(stat -c '%u' /app)"
    app_gid="$(stat -c '%g' /app)"

    if [ "$app_uid" -ne 0 ]; then
        if ! getent group "$app_gid" >/dev/null 2>&1; then
            groupadd -g "$app_gid" hostgroup >/dev/null 2>&1 || true
        fi
        if ! getent passwd "$app_uid" >/dev/null 2>&1; then
            useradd -m -u "$app_uid" -g "$app_gid" hostuser >/dev/null 2>&1 || true
        fi

        if [ "$should_run_migrations" -eq 1 ]; then
            run_migrations_as_user "$app_uid" "$app_gid"
        fi

        exec gosu "$app_uid:$app_gid" "$@"
    fi
fi

if [ "$should_run_migrations" -eq 1 ]; then
    run_migrations
fi

exec "$@"
