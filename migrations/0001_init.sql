CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    ref TEXT NOT NULL UNIQUE,            -- username без @ либо числовой chat_id
    chat_id BIGINT,
    title TEXT,
    username TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    origin TEXT NOT NULL DEFAULT 'config',   -- config | bot
    resolve_error TEXT,
    last_message_id BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bot_users (
    user_id BIGINT PRIMARY KEY,
    lang TEXT NOT NULL DEFAULT 'ru',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE matches (
    id BIGSERIAL PRIMARY KEY,
    source_id INT REFERENCES sources(id) ON DELETE SET NULL,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    chat_title TEXT,
    link TEXT,
    sent_at TIMESTAMPTZ NOT NULL,
    sender_hash TEXT,
    text TEXT NOT NULL,
    score INT NOT NULL,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    direction TEXT NOT NULL,
    route TEXT[] NOT NULL DEFAULT '{}',
    route_names JSONB NOT NULL DEFAULT '{}',
    travel_date DATE,
    date_text TEXT,
    reasons JSONB NOT NULL DEFAULT '[]',
    rules TEXT[] NOT NULL DEFAULT '{}',
    text_hash TEXT NOT NULL,
    simhash BIGINT,
    fingerprint TEXT,
    status TEXT NOT NULL DEFAULT 'new',      -- new | duplicate
    duplicate_of BIGINT REFERENCES matches(id) ON DELETE SET NULL,
    notified_at TIMESTAMPTZ,
    notify_attempts INT NOT NULL DEFAULT 0,
    contact_status TEXT NOT NULL DEFAULT 'none',
    contact_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT matches_msg_uniq UNIQUE (chat_id, message_id)
);
CREATE INDEX matches_created_idx ON matches (created_at);
CREATE INDEX matches_text_hash_idx ON matches (text_hash);
CREATE INDEX matches_fp_idx ON matches (fingerprint) WHERE fingerprint IS NOT NULL;
CREATE INDEX matches_notify_idx ON matches (status, notified_at, score);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    tg_message_id BIGINT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('useful', 'irrelevant', 'duplicate')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (match_id, user_id)
);
