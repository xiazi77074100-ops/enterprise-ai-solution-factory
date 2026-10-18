#!/bin/sh
# Creates the application role (DML only). The owner role (POSTGRES_USER) runs migrations (ADR-004).
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$EASF_APP_DB_PASSWORD" <<'SQL'
CREATE ROLE easf_app LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE easf TO easf_app;
GRANT USAGE ON SCHEMA public TO easf_app;
ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app;
ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO easf_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
