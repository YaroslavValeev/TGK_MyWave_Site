-- Initial PostgreSQL setup for MyWave Safari App
-- This script is automatically executed when the PostgreSQL container starts

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema
CREATE SCHEMA IF NOT EXISTS mywave;

-- Set default schema
ALTER ROLE mywave_user SET search_path TO mywave,public;

-- Create audit tables schema
CREATE SCHEMA IF NOT EXISTS audit;

-- Ensure proper permissions
GRANT ALL PRIVILEGES ON SCHEMA mywave TO mywave_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO mywave_user;
GRANT USAGE ON SCHEMA public TO mywave_user;

-- Log initialization completion
-- (can be checked with: SELECT * FROM pg_catalog.pg_tables WHERE tablename = 'my_init_log' AND schemaname = 'public')
CREATE TABLE IF NOT EXISTS public.init_log (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO public.init_log (message) VALUES ('MyWave Safari database initialized successfully');
