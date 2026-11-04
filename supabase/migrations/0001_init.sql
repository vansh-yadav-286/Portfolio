-- Initial schema for the portfolio backend, generated from the SQLAlchemy
-- models in backend/app/models/. Mirrors what Alembic would have produced;
-- there were no pre-existing Alembic migrations in this repo to port from.
--
-- This runs against Supabase's managed Postgres. The FastAPI backend keeps
-- connecting directly via DATABASE_URL (SQLAlchemy), not through Supabase's
-- PostgREST/supabase-js layer, so RLS below is defense-in-depth rather than
-- the primary access control for the content tables.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

create type user_role as enum ('admin', 'user');
create type contact_status as enum ('unread', 'read', 'replied', 'archived');

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------

create table users (
    id serial primary key,
    name varchar(120) not null,
    email varchar(255) not null unique,
    password_hash varchar(255),
    oauth_provider varchar(20),
    oauth_provider_id varchar(255),
    email_verified boolean not null default false,
    is_active boolean not null default true,
    role user_role not null default 'user',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_users_oauth_provider_identity unique (oauth_provider, oauth_provider_id)
);

-- ---------------------------------------------------------------------------
-- projects
-- ---------------------------------------------------------------------------

create table projects (
    id serial primary key,
    title varchar(200) not null,
    description text not null,
    technologies varchar(500) not null default '',
    image_url varchar(500),
    github_url varchar(500),
    live_url varchar(500),
    category varchar(120),
    featured boolean not null default false,
    display_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_projects_display_order on projects (display_order);

-- ---------------------------------------------------------------------------
-- certificates
-- ---------------------------------------------------------------------------

create table certificates (
    id serial primary key,
    title varchar(200) not null,
    issuer varchar(200) not null,
    issue_date date,
    credential_id varchar(200),
    credential_url varchar(500),
    image_url varchar(500),
    pdf_url varchar(500),
    display_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_certificates_display_order on certificates (display_order);

-- ---------------------------------------------------------------------------
-- hackathons
-- ---------------------------------------------------------------------------

create table hackathons (
    id serial primary key,
    title varchar(200) not null,
    type varchar(20) not null,
    description text not null default '',
    organizer varchar(200),
    date date,
    location varchar(200),
    icon varchar(40),
    image_url varchar(500),
    certificate_url varchar(500),
    event_url varchar(500),
    subitems jsonb,
    is_visible boolean not null default true,
    display_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_hackathons_display_order on hackathons (display_order);

-- ---------------------------------------------------------------------------
-- experiences
-- ---------------------------------------------------------------------------

create table experiences (
    id serial primary key,
    title varchar(200) not null,
    organization varchar(200) not null,
    experience_type varchar(100) not null,
    start_date date,
    end_date date,
    is_current boolean not null default false,
    description text not null,
    link_url varchar(500),
    display_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_experiences_display_order on experiences (display_order);

-- ---------------------------------------------------------------------------
-- contact_messages
-- ---------------------------------------------------------------------------

create table contact_messages (
    id serial primary key,
    name varchar(120) not null,
    email varchar(255) not null,
    subject varchar(200) not null,
    message text not null,
    status contact_status not null default 'unread',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_contact_messages_email on contact_messages (email);

-- ---------------------------------------------------------------------------
-- visitors
-- ---------------------------------------------------------------------------

create table visitors (
    id serial primary key,
    session_id varchar(64) not null,
    page varchar(300) not null,
    referrer varchar(500),
    user_agent varchar(500),
    ip_hash varchar(64),
    visited_at timestamptz not null default now()
);
create index ix_visitors_session_id on visitors (session_id);

-- ---------------------------------------------------------------------------
-- oauth_login_codes
-- ---------------------------------------------------------------------------

create table oauth_login_codes (
    id serial primary key,
    code_hash varchar(64) not null unique,
    user_id integer not null references users (id) on delete cascade,
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);
create index ix_oauth_login_codes_code_hash on oauth_login_codes (code_hash);

-- ---------------------------------------------------------------------------
-- auth_events
-- ---------------------------------------------------------------------------

create table auth_events (
    id serial primary key,
    user_id integer references users (id) on delete set null,
    email varchar(255),
    method varchar(20) not null,
    event_type varchar(20) not null,
    status varchar(20) not null,
    reason varchar(100),
    session_ref varchar(64),
    user_agent varchar(300),
    ip_hash varchar(64),
    created_at timestamptz not null default now()
);
create index ix_auth_events_user_id on auth_events (user_id);
create index ix_auth_events_email on auth_events (email);
create index ix_auth_events_method on auth_events (method);
create index ix_auth_events_event_type on auth_events (event_type);
create index ix_auth_events_status on auth_events (status);
create index ix_auth_events_created_at on auth_events (created_at);
create index ix_auth_events_session_ref on auth_events (session_ref);
create index ix_auth_events_user_id_created_at on auth_events (user_id, created_at);
create index ix_auth_events_event_type_created_at on auth_events (event_type, created_at);

-- ---------------------------------------------------------------------------
-- admin_audit_logs
-- ---------------------------------------------------------------------------

create table admin_audit_logs (
    id serial primary key,
    admin_id integer not null references users (id) on delete cascade,
    action varchar(100) not null,
    target_type varchar(50),
    target_id integer,
    outcome varchar(20) not null default 'success',
    created_at timestamptz not null default now()
);
create index ix_admin_audit_logs_admin_id on admin_audit_logs (admin_id);
create index ix_admin_audit_logs_action on admin_audit_logs (action);
create index ix_admin_audit_logs_created_at on admin_audit_logs (created_at);

-- ---------------------------------------------------------------------------
-- Row Level Security
--
-- The backend connects with the Postgres connection string (full table
-- privileges), so these policies matter only if something other than the
-- backend ever queries this database directly (e.g. via the Supabase
-- dashboard's API layer with the anon key). Public content is readable;
-- everything else default-denies.
-- ---------------------------------------------------------------------------

alter table users enable row level security;
alter table projects enable row level security;
alter table certificates enable row level security;
alter table hackathons enable row level security;
alter table experiences enable row level security;
alter table contact_messages enable row level security;
alter table visitors enable row level security;
alter table oauth_login_codes enable row level security;
alter table auth_events enable row level security;
alter table admin_audit_logs enable row level security;

-- Public, read-only content: visible hackathons/workshops only.
create policy "public read access" on projects
    for select using (true);

create policy "public read access" on certificates
    for select using (true);

create policy "public read access" on hackathons
    for select using (is_visible = true);

create policy "public read access" on experiences
    for select using (true);

-- No policies are created for users, contact_messages, visitors,
-- oauth_login_codes, auth_events, or admin_audit_logs: RLS enabled with zero
-- policies means default-deny for anon/authenticated roles, which is what we
-- want for this data.
