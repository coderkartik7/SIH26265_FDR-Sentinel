-- Enable pg_trgm extension for fast trigram duplicate/fuzzy matching on FDR numbers
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
