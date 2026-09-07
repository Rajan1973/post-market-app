-- Migration 003: Metrics & Rotation Tables (Market Metrics, Stock Metrics, Sector Metrics, Rotation & Events)

-- Market-Level Metrics Table (P0 Fix: Dedicated Market Metrics Table)
CREATE TABLE IF NOT EXISTS market_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    nifty50_close NUMERIC(12,2),
    nifty50_change_pct NUMERIC(6,2),
    sensex_close NUMERIC(12,2),
    sensex_change_pct NUMERIC(6,2),
    nifty_bank_close NUMERIC(12,2),
    nifty_bank_change_pct NUMERIC(6,2),
    india_vix NUMERIC(6,2),
    india_vix_change NUMERIC(6,2),
    fii_cash_net NUMERIC(12,2),
    dii_cash_net NUMERIC(12,2),
    advance_count_n500 INT,
    decline_count_n500 INT,
    ad_ratio_n500 NUMERIC(6,2),
    brent_crude_usd NUMERIC(8,2),
    gold_mcx_inr NUMERIC(10,2),
    usd_inr NUMERIC(8,4),
    regime_composite_score NUMERIC(5,2),
    regime_label VARCHAR(50),
    source_locator TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_metrics_date ON market_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_market_metrics_report ON market_metrics(report_id);

-- Stock Metrics Table
CREATE TABLE IF NOT EXISTS stock_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    ltp NUMERIC(12,2),
    daily_return NUMERIC(6,2),
    weekly_return NUMERIC(6,2),
    monthly_return NUMERIC(6,2),
    volume_x14 NUMERIC(8,2),
    volume_x63 NUMERIC(8,2),
    rsi14 NUMERIC(5,2),
    adx14 NUMERIC(5,2),
    pct_from_20sma NUMERIC(6,2),
    scanner_type VARCHAR(100), -- volume_surge, break_out, high_rsi, high_adx, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_metrics_stock_date ON stock_metrics(stock_id, metric_date);
CREATE INDEX IF NOT EXISTS idx_stock_metrics_report ON stock_metrics(report_id);

-- Sector Metrics Table
CREATE TABLE IF NOT EXISTS sector_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    daily_return NUMERIC(6,2),
    weekly_return NUMERIC(6,2),
    monthly_return NUMERIC(6,2),
    quarterly_return NUMERIC(6,2),
    advance_count INT,
    decline_count INT,
    ad_ratio NUMERIC(6,2),
    pct_above_20dma NUMERIC(5,2),
    pct_above_50dma NUMERIC(5,2),
    pct_above_100dma NUMERIC(5,2),
    pct_above_200dma NUMERIC(5,2),
    breadth_change_5d NUMERIC(6,2),
    rank_1m INT,
    rank_3m INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sector_metrics_sector_date ON sector_metrics(sector_id, metric_date);
CREATE INDEX IF NOT EXISTS idx_sector_metrics_report ON sector_metrics(report_id);

-- Flexible Sector-Specific Metrics Table (For industry-specific operating metrics e.g. Met Coke, GDV, ADR, etc.)
CREATE TABLE IF NOT EXISTS sector_flexible_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID REFERENCES sectors(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    entity_type VARCHAR(50) NOT NULL DEFAULT 'sector', -- sector, company
    entity_name VARCHAR(255) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value TEXT NOT NULL,
    metric_unit VARCHAR(50),
    metric_period VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sector Rotation Table
CREATE TABLE IF NOT EXISTS sector_rotation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    direction VARCHAR(50) NOT NULL, -- rotating_in, rotating_out, neutral
    breadth_change NUMERIC(6,2),
    weekly_return NUMERIC(6,2),
    monthly_rank INT,
    interpretation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Research Events Table
CREATE TABLE IF NOT EXISTS research_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- stock, sector, theme
    entity_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(100) NOT NULL, -- sector_strengthening, stock_scanner_appearance, catalyst, risk, etc.
    title VARCHAR(255) NOT NULL,
    description TEXT,
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section_id UUID REFERENCES report_sections(id) ON DELETE SET NULL,
    importance VARCHAR(20) DEFAULT 'medium',
    confidence NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
