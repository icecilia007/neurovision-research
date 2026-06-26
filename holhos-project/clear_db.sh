#!/bin/bash
set -e

CONTAINER="questionarios_db"
DB="formularios_db"
USER="postgres"

echo "Limpando todas as tabelas do banco '$DB' no container '$CONTAINER'..."

docker exec -i $CONTAINER psql -U $USER -d $DB <<'EOSQL'
DO $$ DECLARE
    r RECORD;
BEGIN
    -- Truncar todas as tabelas no schema public
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'TRUNCATE TABLE public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;

DO $$ DECLARE
    r RECORD;
BEGIN
    -- Resetar todas as sequências (IDs voltam a 1)
    FOR r IN (SELECT c.oid::regclass::text as seqname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE c.relkind = 'S' AND n.nspname = 'public') LOOP
        EXECUTE 'ALTER SEQUENCE ' || r.seqname || ' RESTART WITH 1';
    END LOOP;
END $$;
EOSQL

echo "Banco de dados limpo com sucesso!"
