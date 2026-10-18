#!/bin/sh
# Creates the application role (DML only) and the test database. The owner role (POSTGRES_USER) runs
# migrations (ADR-004). Tests use only <db>_test, so running them never touches development data (P2-00).
set -eu
TEST_DB="${POSTGRES_DB}_test"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$EASF_APP_DB_PASSWORD" -v test_db="$TEST_DB" <<'SQL'
CREATE ROLE easf_app LOGIN PASSWORD :'app_password';
CREATE DATABASE :"test_db" OWNER easf_owner;
REVOKE CONNECT ON DATABASE :"test_db" FROM PUBLIC;
SQL

# Privileges are per database: apply the same grants to both.
for db in "$POSTGRES_DB" "$TEST_DB"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -v db="$db" <<'SQL'
GRANT CONNECT ON DATABASE :"db" TO easf_app;
GRANT USAGE ON SCHEMA public TO easf_app;
ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app;
ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO easf_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
done
