-- Migration 004: Signals & Signal Evidence Tables

-- Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- stock, sector, theme
    entity_id UUID NOT NULL,
    signal_type VARCHAR(100) NOT NULL, -- breadth_breakout, momentum_shift, guidance_beat, volume_surge
    signal_state VARCHAR(50) NOT NULL DEFAULT 'active', -- active, historical, invalidated
    confidence NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    evidence_count INT NOT NULL DEFAULT 1,
    source_count INT NOT NULL DEFAULT 1,
    first_detected DATE NOT NULL,
    last_updated DATE NOT NULL,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Signal Evidence Table
CREATE TABLE IF NOT EXISTS signal_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    evidence_type VARCHAR(100) NOT NULL, -- metric_threshold, scanner_match, narrative_event
    metric VARCHAR(100),
    value TEXT,
    direction VARCHAR(20), -- bullish, bearish, neutral
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    section_id UUID REFERENCES report_sections(id) ON DELETE SET NULL,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
