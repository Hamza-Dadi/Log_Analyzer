-- ========================================================
-- Schema PostgreSQL pour le projet Log Analyzer
-- Table de securite et index de performance
-- ========================================================

CREATE TABLE IF NOT EXISTS security_logs (
    id SERIAL PRIMARY KEY,
    month VARCHAR(10),
    day INTEGER,
    time VARCHAR(20),
    hour INTEGER,
    service VARCHAR(50),
    event_type VARCHAR(50),
    username VARCHAR(100),
    ip_address VARCHAR(50),
    country VARCHAR(10),
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour accelerer les requetes d'agregation
CREATE INDEX IF NOT EXISTS idx_security_country ON security_logs(country);
CREATE INDEX IF NOT EXISTS idx_security_ip ON security_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_security_event ON security_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_security_hour ON security_logs(hour);
CREATE INDEX IF NOT EXISTS idx_security_user ON security_logs(username);
