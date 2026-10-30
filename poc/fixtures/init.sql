\set ON_ERROR_STOP on
\getenv fixture_password BYTEBASE_POC_DB_PASSWORD

SELECT format('CREATE ROLE poc LOGIN PASSWORD %L', :'fixture_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'poc') \gexec
SELECT 'CREATE DATABASE sandbox_poc OWNER poc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sandbox_poc') \gexec
SELECT 'CREATE DATABASE prod_poc OWNER poc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prod_poc') \gexec

\connect sandbox_poc
SET ROLE poc;
CREATE TABLE IF NOT EXISTS public.permission_fixture (id integer PRIMARY KEY, value text NOT NULL);
INSERT INTO public.permission_fixture VALUES (1, 'sandbox fixture') ON CONFLICT (id) DO NOTHING;

\connect prod_poc
SET ROLE poc;
CREATE TABLE IF NOT EXISTS public.permission_fixture (id integer PRIMARY KEY, value text NOT NULL);
INSERT INTO public.permission_fixture VALUES (1, 'production fixture') ON CONFLICT (id) DO NOTHING;
