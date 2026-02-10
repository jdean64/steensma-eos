-- VTO (Vision/Traction Organizer) Database Schema

CREATE TABLE IF NOT EXISTS vto_core_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value_text TEXT NOT NULL,
    sort_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS vto_core_focus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passion TEXT,
    niche TEXT,
    cash_flow_driver TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS vto_core_target (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_text TEXT NOT NULL,
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS vto_marketing_strategy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uniques TEXT,
    guarantee TEXT,
    proven_process TEXT,
    target_market TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS vto_three_year_picture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    future_date DATE,
    revenue TEXT,
    profit TEXT,
    measurables TEXT,
    what_does_it_look_like TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS vto_one_year_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    future_date DATE,
    revenue TEXT,
    profit TEXT,
    measurables TEXT,
    goals TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- History tables for lifecycle tracking
CREATE TABLE IF NOT EXISTS vto_core_values_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    core_value_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (core_value_id) REFERENCES vto_core_values(id)
);

CREATE TABLE IF NOT EXISTS vto_core_focus_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    core_focus_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (core_focus_id) REFERENCES vto_core_focus(id)
);

CREATE TABLE IF NOT EXISTS vto_core_target_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    core_target_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (core_target_id) REFERENCES vto_core_target(id)
);

CREATE TABLE IF NOT EXISTS vto_marketing_strategy_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marketing_strategy_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (marketing_strategy_id) REFERENCES vto_marketing_strategy(id)
);

CREATE TABLE IF NOT EXISTS vto_three_year_picture_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    three_year_picture_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (three_year_picture_id) REFERENCES vto_three_year_picture(id)
);

CREATE TABLE IF NOT EXISTS vto_one_year_plan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    one_year_plan_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_note TEXT,
    FOREIGN KEY (one_year_plan_id) REFERENCES vto_one_year_plan(id)
);
