-- L10 Meeting Database Schema

CREATE TABLE IF NOT EXISTS l10_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_date DATE NOT NULL,
    team_name TEXT DEFAULT 'Plainwell Team Lead',
    start_time TEXT DEFAULT '7:30 am',
    status TEXT DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, COMPLETED
    meeting_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

CREATE TABLE IF NOT EXISTS l10_agenda_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    section_name TEXT NOT NULL,
    time_allocated INTEGER, -- minutes
    sort_order INTEGER,
    status TEXT DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETE
    notes TEXT,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

-- Standard agenda: Segue, Headlines, Scorecard Review, Rock Review, To-Do Review, IDS, New To-Dos, Conclude
CREATE TABLE IF NOT EXISTS l10_agenda_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_name TEXT NOT NULL,
    time_allocated INTEGER,
    sort_order INTEGER,
    description TEXT
);

CREATE TABLE IF NOT EXISTS l10_todos_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    todo_text TEXT NOT NULL,
    who TEXT,
    done BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

CREATE TABLE IF NOT EXISTS l10_new_todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    todo_text TEXT NOT NULL,
    who TEXT,
    due_date DATE,
    created_during_meeting BOOLEAN DEFAULT 1,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

CREATE TABLE IF NOT EXISTS l10_issues_discussed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    issue_id INTEGER, -- Links to issues table
    priority TEXT,
    discussed BOOLEAN DEFAULT 0,
    resolved BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id),
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE TABLE IF NOT EXISTS l10_headlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    headline_type TEXT, -- 'CUSTOMER' or 'EMPLOYEE'
    sentiment TEXT, -- 'GOOD' or 'BAD'
    headline_text TEXT NOT NULL,
    who_reported TEXT,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

CREATE TABLE IF NOT EXISTS l10_cascading_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    message_text TEXT NOT NULL,
    who_delivers TEXT,
    sort_order INTEGER,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

CREATE TABLE IF NOT EXISTS l10_meeting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    action TEXT,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES l10_meetings(id)
);

-- Insert standard L10 agenda template
INSERT OR IGNORE INTO l10_agenda_templates (section_name, time_allocated, sort_order, description) VALUES
('Segue', 5, 1, 'Personal and Business Best News'),
('Headlines', 5, 2, 'Customer/Employee Good and Bad Reports'),
('Scorecard Review', 5, 3, 'Review weekly measurables - On Track / Off Track'),
('Rock Review', 5, 4, 'Review quarterly rocks - On Track / Off Track'),
('To-Do List Review', 5, 5, 'Review last week''s to-dos - Done / Not Done'),
('IDS', 60, 6, 'Identify, Discuss, Solve - Work through issues list'),
('New To-Dos', 5, 7, 'Create action items from IDS'),
('Conclude', 5, 8, 'Cascading messages, rating, close on time');
