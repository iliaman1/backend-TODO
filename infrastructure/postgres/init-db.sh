#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE auth_db;
    CREATE DATABASE todo_db;
    CREATE DATABASE files_db;
EOSQL
