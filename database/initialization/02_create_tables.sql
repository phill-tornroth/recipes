-- 02_create_tables.sql

-- Connect to the recipes database
\c recipes

ALTER DATABASE recipes OWNER TO recipe_user;
CREATE EXTENSION vector;

-- Create the users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Create the recipes table if it doesn't exist
CREATE TABLE IF NOT EXISTS recipes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contents TEXT NOT NULL,
    embedding vector(1536) -- dimensions for text-embedding-3-small
);

-- Create an index on the embedding column for similarity search
CREATE INDEX IF NOT EXISTS idx_recipes_embedding ON recipes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create me
INSERT INTO users (id, email, password)
VALUES (1, 'famousactress@gmail.com', '')
ON CONFLICT (id) DO NOTHING;