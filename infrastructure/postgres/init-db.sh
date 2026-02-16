#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    ALTER USER "$POSTGRES_USER" WITH CREATEDB;
EOSQL
