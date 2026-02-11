-- =====================================================
-- EOS Platform - Multi-Tenant Hierarchical Schema
-- Version 2.0 - Built for Steensma Enterprises
-- =====================================================
--
-- HIERARCHY:
-- Corporate (steensma) 
--   └─ Divisions (plainwell, kalamazoo, generator, western, etc.)
--      └─ Users (assigned to divisions, with roles)
--
-- =====================================================

-- =====================================================
-- CORE ORGANIZATION & AUTHENTICATION
-- =====================================================

-- Organizations (Parent Level - e.g., "Steensma")
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,  -- e.g., 'steensma'
    display_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Divisions (Second Level - e.g., "Plainwell", "Kalamazoo")
CREATE TABLE IF NOT EXISTS divisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,  -- e.g., 'plainwell'
    full_slug TEXT NOT NULL UNIQUE,  -- e.g., 'steensma.plainwell'
    display_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,  -- user_id
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    UNIQUE(organization_id, slug)
);

-- Users with Multi-Tenant RBAC
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    password_hash TEXT,  -- bcrypt hashed
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- User Roles (Role-Based Access Control)
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,  -- 'PARENT_ADMIN', 'DIVISION_ADMIN', 'USER_RW', 'USER_RO'
    display_name TEXT NOT NULL,
    description TEXT,
    level INTEGER NOT NULL,  -- 1=Parent, 2=Division, 3=User
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert standard roles
INSERT OR IGNORE INTO roles (name, display_name, description, level) VALUES
    ('PARENT_ADMIN', 'Parent Administrator', 'Full access to all divisions and data', 1),
    ('DIVISION_ADMIN', 'Division Administrator', 'Full access to assigned division only', 2),
    ('USER_RW', 'Read-Write User', 'Can view and edit within assigned division', 3),
    ('USER_RO', 'Read-Only User', 'Can only view data within assigned division', 3);

-- User Role Assignments (Many-to-Many with scope)
CREATE TABLE IF NOT EXISTS user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    organization_id INTEGER,  -- NULL for parent admins (access all)
    division_id INTEGER,      -- NULL for parent/org admins
    assigned_by INTEGER,      -- user_id who granted this role
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE(user_id, role_id, organization_id, division_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_division ON user_roles(division_id);
CREATE INDEX IF NOT EXISTS idx_divisions_org ON divisions(organization_id);
CREATE INDEX IF NOT EXISTS idx_divisions_slug ON divisions(full_slug);

-- =====================================================
-- VTO (VISION/TRACTION ORGANIZER) - Hierarchical Cascade
-- =====================================================

-- VTO lives at both organization and division levels
CREATE TABLE IF NOT EXISTS vto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,  -- NULL = corporate/parent VTO
    division_id INTEGER,      -- NULL = parent VTO, populated = division VTO
    
    -- 10-Year Target
    ten_year_target TEXT,
    
    -- 3-Year Picture
    three_year_revenue TEXT,
    three_year_profit TEXT,
    three_year_measurables TEXT,
    
    -- 1-Year Plan
    one_year_revenue TEXT,
    one_year_profit TEXT,
    one_year_goals TEXT,
    
    -- Core Values
    core_values TEXT,  -- JSON array
    
    -- Core Focus (Purpose/Niche)
    core_purpose TEXT,
    core_niche TEXT,
    
    -- Marketing Strategy
    target_market TEXT,
    unique_value_proposition TEXT,
    proven_process TEXT,
    guarantee TEXT,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    effective_date TEXT,
    
    -- Inheritance (for divisions)
    inherits_from_parent BOOLEAN DEFAULT 1,  -- Does division inherit parent VTO?
    parent_vto_id INTEGER,  -- Links to parent VTO
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (parent_vto_id) REFERENCES vto(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- =====================================================
-- ROCKS (QUARTERLY PRIORITIES)
-- =====================================================

CREATE TABLE IF NOT EXISTS rocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER,  -- NULL = parent-level rock
    
    -- Rock Details
    description TEXT NOT NULL,
    owner_user_id INTEGER,
    owner_name TEXT,  -- Fallback if no user assigned
    status TEXT DEFAULT 'NOT STARTED',  -- NOT STARTED, ON TRACK, AT RISK, BLOCKED, COMPLETE
    due_date TEXT,
    progress INTEGER DEFAULT 0,  -- 0-100%
    
    -- Timing
    quarter TEXT NOT NULL,  -- e.g., 'Q1 2026'
    year INTEGER NOT NULL,
    
    -- IDS Notes
    discussion_notes TEXT,  -- For L10 discussions
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- =====================================================
-- SCORECARD (WEEKLY METRICS)
-- =====================================================

CREATE TABLE IF NOT EXISTS scorecard_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER,  -- NULL = parent-level metric
    
    -- Metric Details
    metric_name TEXT NOT NULL,
    owner_user_id INTEGER,
    owner_name TEXT,
    goal TEXT,  -- Target value (can be text like "$100K" or "85%")
    
    -- Weekly Data (last 13 weeks)
    week_1 REAL,
    week_2 REAL,
    week_3 REAL,
    week_4 REAL,
    week_5 REAL,
    week_6 REAL,
    week_7 REAL,
    week_8 REAL,
    week_9 REAL,
    week_10 REAL,
    week_11 REAL,
    week_12 REAL,
    week_13 REAL,
    
    -- Status
    status TEXT DEFAULT 'YELLOW',  -- GREEN, YELLOW, RED
    
    -- Timing
    quarter TEXT,
    year INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- =====================================================
-- ISSUES LIST (IDS - IDENTIFY, DISCUSS, SOLVE)
-- =====================================================

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER,  -- NULL = parent-level issue
    
    -- Issue Details
    issue TEXT NOT NULL,
    category TEXT,  -- SALES, SERVICE, PROCESS, PARTS, ADMINISTRATIVE
    priority TEXT DEFAULT 'MEDIUM',  -- HIGH, MEDIUM, LOW
    owner_user_id INTEGER,
    owner_name TEXT,
    date_added TEXT,
    
    -- IDS Workflow
    ids_stage TEXT DEFAULT 'IDENTIFY',  -- IDENTIFY, DISCUSS, SOLVE, RESOLVED
    discussion_notes TEXT,  -- For DISCUSS stage
    solution TEXT,  -- For SOLVE stage
    
    -- Status
    status TEXT DEFAULT 'OPEN',  -- OPEN, IN PROGRESS, RESOLVED
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    
    -- L10 Linkage
    added_from_l10_id INTEGER,  -- Which L10 spawned this issue?
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    created_by INTEGER,  -- Who added the issue
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (resolved_by) REFERENCES users(id),
    FOREIGN KEY (added_from_l10_id) REFERENCES l10_meetings(id)
);

-- =====================================================
-- TO-DOS (ACTION ITEMS)
-- =====================================================

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER,  -- NULL = parent-level todo
    
    -- To-Do Details
    task TEXT NOT NULL,
    owner_user_id INTEGER,
    owner_name TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'OPEN',  -- OPEN, IN PROGRESS, COMPLETE
    
    -- Source Tracking
    source TEXT,  -- 'L10', 'ISSUE', 'MANUAL', 'ROCK'
    source_l10_id INTEGER,  -- Which L10 meeting spawned this?
    source_issue_id INTEGER,  -- Which issue spawned this?
    source_rock_id INTEGER,  -- Which rock is this related to?
    
    -- Completion
    completed_at TIMESTAMP,
    completed_by INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    created_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (owner_user_id) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (completed_by) REFERENCES users(id),
    FOREIGN KEY (source_l10_id) REFERENCES l10_meetings(id),
    FOREIGN KEY (source_issue_id) REFERENCES issues(id),
    FOREIGN KEY (source_rock_id) REFERENCES rocks(id)
);

-- =====================================================
-- L10 MEETINGS (WEEKLY/BI-WEEKLY MEETINGS)
-- =====================================================

CREATE TABLE IF NOT EXISTS l10_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER NOT NULL,  -- L10s are division-specific
    
    -- Meeting Details
    meeting_date TEXT NOT NULL,
    meeting_time TEXT,
    frequency TEXT DEFAULT 'WEEKLY',  -- WEEKLY, BIWEEKLY, MONTHLY
    duration_minutes INTEGER DEFAULT 90,
    
    -- Meeting Status
    status TEXT DEFAULT 'SCHEDULED',  -- SCHEDULED, IN_PROGRESS, COMPLETED
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Attendees (JSON array of user_ids)
    attendees JSON,  -- [1, 2, 3, 4, 5]
    attendee_names JSON,  -- ["Jeff", "Kurt", "Brian", "Tammy", "Don"]
    
    -- Meeting Notes
    segue_good_news TEXT,
    scorecard_review TEXT,
    rock_review TEXT,
    customer_employee_headlines TEXT,
    
    -- IDS Summary (generated)
    issues_discussed JSON,  -- Array of issue_ids
    todos_created JSON,  -- Array of todo_ids
    
    -- Meeting Recording (future)
    recording_url TEXT,
    transcript_text TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    facilitator_user_id INTEGER,  -- Who ran the meeting
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (facilitator_user_id) REFERENCES users(id)
);

-- L10 Meeting Sections (agenda items with timing)
CREATE TABLE IF NOT EXISTS l10_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    l10_meeting_id INTEGER NOT NULL,
    
    -- Section Details
    section_name TEXT NOT NULL,  -- 'Segue', 'Scorecard', 'Rock Review', 'Headlines', 'To-Do Review', 'IDS', 'Conclude'
    section_order INTEGER NOT NULL,
    allocated_minutes INTEGER NOT NULL,
    actual_minutes INTEGER,
    
    -- Section Status
    status TEXT DEFAULT 'PENDING',  -- PENDING, ACTIVE, COMPLETE
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Section Notes
    notes TEXT,
    
    FOREIGN KEY (l10_meeting_id) REFERENCES l10_meetings(id)
);

-- =====================================================
-- ACCOUNTABILITY CHART
-- =====================================================

CREATE TABLE IF NOT EXISTS accountability_chart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    division_id INTEGER,  -- NULL = parent-level seat
    
    -- Seat Details
    seat_name TEXT NOT NULL,  -- e.g., "Visionary", "Integrator", "Sales Manager"
    seat_description TEXT,
    reports_to_seat_id INTEGER,  -- Hierarchical reporting structure
    
    -- 5 Roles per Seat
    role_1 TEXT,
    role_2 TEXT,
    role_3 TEXT,
    role_4 TEXT,
    role_5 TEXT,
    
    -- Who's in the seat
    user_id INTEGER,  -- Current person in this seat
    user_name TEXT,  -- Fallback
    
    -- GWC (Get It, Want It, Capacity)
    gwc_get_it BOOLEAN DEFAULT 0,
    gwc_want_it BOOLEAN DEFAULT 0,
    gwc_capacity BOOLEAN DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (reports_to_seat_id) REFERENCES accountability_chart(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- =====================================================
-- HISTORY & AUDIT TABLES
-- =====================================================

-- Rocks History
CREATE TABLE IF NOT EXISTS rocks_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rock_id INTEGER NOT NULL,
    field_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (rock_id) REFERENCES rocks(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- Issues History
CREATE TABLE IF NOT EXISTS issues_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    field_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (issue_id) REFERENCES issues(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- Global Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    division_id INTEGER,
    user_id INTEGER,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL,  -- INSERT, UPDATE, DELETE, LOGIN, LOGOUT
    changes JSON,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (division_id) REFERENCES divisions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- =====================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_rocks_org_div ON rocks(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_rocks_quarter ON rocks(quarter, year);
CREATE INDEX IF NOT EXISTS idx_scorecard_org_div ON scorecard_metrics(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_issues_org_div ON issues(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_todos_org_div ON todos(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status);
CREATE INDEX IF NOT EXISTS idx_l10_org_div ON l10_meetings(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_l10_date ON l10_meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_accountability_org_div ON accountability_chart(organization_id, division_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_table ON audit_log(table_name, record_id);

-- =====================================================
-- SEED DATA - STEENSMA ORGANIZATION
-- =====================================================

-- Create parent organization
INSERT OR IGNORE INTO organizations (id, name, slug, display_name) VALUES
    (1, 'Steensma', 'steensma', 'Steensma Enterprises');

-- Create divisions
INSERT OR IGNORE INTO divisions (organization_id, name, slug, full_slug, display_name) VALUES
    (1, 'Plainwell', 'plainwell', 'steensma.plainwell', 'Steensma Plainwell'),
    (1, 'Kalamazoo', 'kalamazoo', 'steensma.kalamazoo', 'Steensma Kalamazoo'),
    (1, 'Generator', 'generator', 'steensma.generator', 'Steensma Generator'),
    (1, 'Western', 'western', 'steensma.western', 'Steensma Western');

-- Create parent admin users (passwords need to be hashed in application)
INSERT OR IGNORE INTO users (id, username, email, full_name) VALUES
    (1, 'brian', 'brian@steensma.com', 'Brian Steensma'),
    (2, 'kurt', 'kurt@steensma.com', 'Kurt Steensma'),
    (3, 'tammy', 'tammy@steensma.com', 'Tammy');

-- Assign parent admin roles
INSERT OR IGNORE INTO user_roles (user_id, role_id, organization_id, division_id) VALUES
    (1, 1, 1, NULL),  -- Brian = Parent Admin
    (2, 1, 1, NULL),  -- Kurt = Parent Admin
    (3, 1, 1, NULL);  -- Tammy = Parent Admin

-- =====================================================
-- END OF SCHEMA
-- =====================================================
