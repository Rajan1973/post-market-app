-- Migration 002: Entity Tables (Sectors, Stocks, Themes, Entity Aliases, Mentions & Unresolved Queue)

-- Sectors Table
CREATE TABLE IF NOT EXISTS sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    benchmark VARCHAR(255),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Stocks Table
CREATE TABLE IF NOT EXISTS stocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'NSE',
    sector_id UUID REFERENCES sectors(id) ON DELETE SET NULL,
    industry VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_exchange_symbol UNIQUE (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);

-- Themes Table
CREATE TABLE IF NOT EXISTS themes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Entity Aliases Table
CREATE TABLE IF NOT EXISTS entity_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- stock, sector, theme
    entity_id UUID NOT NULL,
    alias VARCHAR(255) NOT NULL,
    alias_type VARCHAR(50) NOT NULL DEFAULT 'ticker', -- ticker, company_name, common_name
    confidence NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_alias_entity UNIQUE (entity_type, alias)
);

CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias ON entity_aliases(alias);

-- Report Mentions Table
CREATE TABLE IF NOT EXISTS report_mentions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL, -- stock, sector, theme
    entity_id UUID NOT NULL,
    section_id UUID REFERENCES report_sections(id) ON DELETE SET NULL,
    mention_type VARCHAR(50) NOT NULL DEFAULT 'scanner', -- scanner, narrative, thesis, top_mover
    excerpt TEXT,
    importance VARCHAR(20) DEFAULT 'medium', -- high, medium, low
    source_locator TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_mentions_report ON report_mentions(report_id);
CREATE INDEX IF NOT EXISTS idx_report_mentions_entity ON report_mentions(entity_type, entity_id);

-- Unresolved Entities Queue Table
CREATE TABLE IF NOT EXISTS unresolved_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- stock, sector, theme
    candidate_matches JSONB,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0.00,
    source_report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, resolved, ignored
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
