-- 01_create_user_and_db.sql



DO
$$
BEGIN
   -- Create the recipe_user if it doesn't exist
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'recipe_user') THEN

      CREATE USER recipe_user WITH PASSWORD 'bananabread' SUPERUSER CREATEDB;
   END IF;

   -- Create the recipes database if it doesn't exist
   IF NOT EXISTS (
      SELECT FROM pg_database
      WHERE datname = 'recipes') THEN

      CREATE DATABASE recipes OWNER recipe_user;
      ALTER DATABASE recipes SET ivfflat.iterative_scan = relaxed_order;
   END IF;
END
$$;
