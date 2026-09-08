-- Create databases if they do not exist
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

-- Connect to churn_db (or execute schema creation on default churn_db)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS scoring;

-- Create Raw Ingestion Table
CREATE TABLE IF NOT EXISTS raw.telco_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    gender VARCHAR(20),
    senior_citizen INTEGER,
    partner VARCHAR(10),
    dependents VARCHAR(10),
    tenure INTEGER,
    phone_service VARCHAR(10),
    multiple_lines VARCHAR(30),
    internet_service VARCHAR(30),
    online_security VARCHAR(30),
    online_backup VARCHAR(30),
    device_protection VARCHAR(30),
    tech_support VARCHAR(30),
    streaming_tv VARCHAR(30),
    streaming_movies VARCHAR(30),
    contract VARCHAR(30),
    paperless_billing VARCHAR(10),
    payment_method VARCHAR(50),
    monthly_charges NUMERIC(10, 2),
    total_charges NUMERIC(10, 2),
    churn VARCHAR(10),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Churn Scores Table for Phase 3 scoring
CREATE TABLE IF NOT EXISTS scoring.churn_scores (
    customer_id VARCHAR(50),
    churn_probability NUMERIC(5, 4),
    risk_tier VARCHAR(20),
    top_reasons TEXT,
    model_version VARCHAR(50),
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id, scored_at)
);

CREATE INDEX IF NOT EXISTS idx_churn_scores_scored_at ON scoring.churn_scores(scored_at);
CREATE INDEX IF NOT EXISTS idx_churn_scores_risk_tier ON scoring.churn_scores(risk_tier);
