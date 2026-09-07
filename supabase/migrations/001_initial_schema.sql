-- Migration 001: Initial Schema (Extensions, Core Types, Reports & Report Sections)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type VARCHAR(50) NOT NULL, -- EOD, SECTOR_RESEARCH, UNKNOWN
    title VARCHAR(255) NOT NULL,
    subtitle TEXT,
    report_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    source_filename VARCHAR(255) NOT NULL,
    source_path TEXT NOT NULL,
    source_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 for duplicate detection
    source_format VARCHAR(20) NOT NULL DEFAULT 'html',
    headline TEXT,
    standfirst TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'imported', -- discovered, parsing, parsed, validated, imported, failed
    storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_report_date ON reports(report_date);
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_source_hash ON reports(source_hash);

-- Report Sections Table
CREATE TABLE IF NOT EXISTS report_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section_code VARCHAR(50) NOT NULL, -- e.g. s1, s2, s8, thesis, scissor
    section_number INT,
    section_title VARCHAR(255) NOT NULL,
    section_group VARCHAR(10), -- A, B, C, D
    content TEXT NOT NULL,
    source_locator TEXT NOT NULL, -- Provenance (e.g. 2026-09-04-daily-brief.html#s8)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_sections_report ON report_sections(report_id);
CREATE INDEX IF NOT EXISTS idx_report_sections_code ON report_sections(section_code);
