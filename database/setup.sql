
CREATE TABLE coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(6) NOT NULL UNIQUE,
    discount_type VARCHAR(20) NOT NULL,
    discount_value FLOAT NOT NULL,
    validity_start DATETIME,
    validity_end DATETIME,
    user_age_group VARCHAR,
    days_from_signup VARCHAR,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
