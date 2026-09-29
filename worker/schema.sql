CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'Técnico',
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS appointments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_number TEXT UNIQUE,
  title TEXT NOT NULL,
  type TEXT NOT NULL,
  requester TEXT NOT NULL,
  department TEXT DEFAULT '',
  location TEXT DEFAULT '',
  technician TEXT DEFAULT '',
  start TEXT NOT NULL,
  end TEXT NOT NULL,
  priority TEXT DEFAULT 'Normal',
  status TEXT DEFAULT 'Agendado',
  description TEXT DEFAULT '',
  notes TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_appointments_start ON appointments(start);
