-- 02_create_tables.sql

-- Connect to the recipes database
\c recipes

ALTER DATABASE recipes OWNER TO recipe_user;

-- Create the users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Create the recipes table if it doesn't exist
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    contents TEXT NOT NULL
);

-- Create me
INSERT INTO users (id, email, password)
VALUES ('1d7bec80-9ea3-4359-8707-2fffd74a925a', 'famousactress@gmail.com', '')
ON CONFLICT (id) DO NOTHING;