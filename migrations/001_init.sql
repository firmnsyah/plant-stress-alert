PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plants (
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  treatment TEXT NOT NULL CHECK (treatment IN ('kontrol','panas','salinitas','kekeringan')),
  planted_at TEXT,
  stress_started_at TEXT,
  first_wilt_at TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY,
  plant_id INTEGER NOT NULL REFERENCES plants(id),
  observed_at TEXT NOT NULL,
  day_after_treatment INTEGER,
  bioelectric_mv REAL,
  leaf_temp_c REAL NOT NULL CHECK (leaf_temp_c BETWEEN 10 AND 60),
  air_temp_c REAL NOT NULL CHECK (air_temp_c BETWEEN 10 AND 60),
  ec1_us REAL NOT NULL CHECK (ec1_us > 0),
  ec2_us REAL NOT NULL CHECK (ec2_us > 0 AND ec1_us <= ec2_us),
  el_percent REAL NOT NULL CHECK (el_percent >= 0 AND el_percent <= 100),
  wilt_score INTEGER NOT NULL CHECK (wilt_score BETWEEN 0 AND 4),
  notes TEXT,
  deleted_at TEXT,
  UNIQUE (plant_id, observed_at)
);

CREATE TABLE IF NOT EXISTS leaf_images (
  id INTEGER PRIMARY KEY,
  observation_id INTEGER NOT NULL REFERENCES observations(id),
  file_path TEXT NOT NULL,
  r REAL, g REAL, b REAL, h REAL, s REAL, v REAL,
  dgci REAL, exg REAL, leaf_pixels INTEGER NOT NULL,
  hsv_low TEXT NOT NULL, hsv_high TEXT NOT NULL,
  has_gray_card INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS config_versions (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  note TEXT,
  settings_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_results (
  id INTEGER PRIMARY KEY,
  observation_id INTEGER NOT NULL REFERENCES observations(id),
  config_id INTEGER NOT NULL REFERENCES config_versions(id),
  norm_bio REAL, norm_temp REAL, norm_color REAL, norm_el REAL,
  stress_index REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('Normal','Warning','High Stress','Data Tidak Valid')),
  nearest_treatment TEXT, nearest_distance REAL,
  second_treatment TEXT, second_distance REAL,
  ambiguous INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_observations_plant_time
  ON observations(plant_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_analysis_observation
  ON analysis_results(observation_id);
