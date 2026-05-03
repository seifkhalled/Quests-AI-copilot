CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS insights CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS candidate_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    full_name text,
    role text NOT NULL CHECK (role IN ('poster', 'candidate')),
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE candidate_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name text,
    phone text,
    summary text,
    tech_stack text[] DEFAULT '{}',
    preferred_roles text[] DEFAULT '{}',
    experience_years integer,
    updated_at timestamptz DEFAULT now()
);

CREATE TRIGGER update_candidate_profiles_updated_at BEFORE UPDATE ON candidate_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by uuid REFERENCES users(id) ON DELETE SET NULL,
    title text NOT NULL,
    source_type text NOT NULL CHECK (source_type IN ('pdf', 'txt', 'md', 'slack_json')),
    raw_text text,
    metadata jsonb DEFAULT '{}',
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    token_count integer,
    qdrant_point_id text UNIQUE,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title text,
    scope text NOT NULL DEFAULT 'global' CHECK (scope IN ('global', 'document_scoped')),
    scoped_document_id uuid,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    created_at timestamptz DEFAULT now(),
    last_message_at timestamptz DEFAULT now()
);

CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    content text NOT NULL,
    sources jsonb DEFAULT '[]',
    confidence float,
    reasoning text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    body text NOT NULL,
    category text NOT NULL CHECK (category IN ('conflict', 'pattern', 'decision', 'issue')),
    source_document_ids jsonb DEFAULT '[]',
    relevance_score float,
    generated_at timestamptz DEFAULT now()
);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_qdrant_point_id ON chunks(qdrant_point_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_status ON documents(status);
