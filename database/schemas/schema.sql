-- Reference PostgreSQL schema for the portfolio database.
-- This file documents the schema; it is not applied directly. The schema is
-- created and versioned by Alembic (see database/migrations/alembic/versions).

CREATE TYPE user_role AS ENUM ('admin', 'user');
CREATE TYPE contact_status AS ENUM ('unread', 'read', 'replied', 'archived');

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120)  NOT NULL,
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    role            user_role     NOT NULL DEFAULT 'user',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE projects (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200)  NOT NULL,
    description     TEXT          NOT NULL,
    technologies    VARCHAR(500)  NOT NULL DEFAULT '',
    image_url       VARCHAR(500),
    github_url      VARCHAR(500),
    live_url        VARCHAR(500),
    category        VARCHAR(120),
    featured        BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE certificates (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200)  NOT NULL,
    issuer          VARCHAR(200)  NOT NULL,
    issue_date      DATE,
    credential_id   VARCHAR(200),
    credential_url  VARCHAR(500),
    image_url       VARCHAR(500),
    pdf_url         VARCHAR(500),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE contact_messages (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120)  NOT NULL,
    email           VARCHAR(255)  NOT NULL,
    subject         VARCHAR(200)  NOT NULL,
    message         TEXT          NOT NULL,
    status          contact_status NOT NULL DEFAULT 'unread',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_contact_messages_email ON contact_messages (email);

CREATE TABLE visitors (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(64)   NOT NULL,
    page            VARCHAR(300)  NOT NULL,
    referrer        VARCHAR(500),
    user_agent      VARCHAR(500),
    ip_hash         VARCHAR(64),
    visited_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_visitors_session_id ON visitors (session_id);
