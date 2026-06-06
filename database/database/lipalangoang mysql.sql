-- ═══════════════════════════════════════════════════════════════
-- URBAN CAB — MySQL Schema (v3.0)
-- Maseru CBD + MSU Local Passenger Transportation System
-- Anonymous passenger model: name + phone inline on Rides
-- 8 tables | 3NF | MySQL 5.7+ / MariaDB 10.3+
--
-- HOW TO USE:
--   mysql -u root -p < urban_cab_mysql.sql
--   OR open in MySQL Workbench and run the whole script.
--
-- This script:
--   1. Creates the database urban_cab_db (drops if it exists)
--   2. Creates all 8 tables with correct types, constraints, FKs
--   3. Seeds all reference data and sample records
-- ═══════════════════════════════════════════════════════════════

-- ── Create & select database ──────────────────────────────────
DROP DATABASE IF EXISTS urban_cab_db;
CREATE DATABASE urban_cab_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE urban_cab_db;

-- ── 1. Locations ──────────────────────────────────────────────
CREATE TABLE Locations (
  location_id   INT          NOT NULL AUTO_INCREMENT,
  location_name VARCHAR(120) NOT NULL,
  area_zone     VARCHAR(40)  NOT NULL DEFAULT 'CBD',
  description   VARCHAR(255)          DEFAULT NULL,
  is_active     TINYINT(1)   NOT NULL DEFAULT 1,
  PRIMARY KEY (location_id),
  UNIQUE KEY uq_location_name (location_name)
) ENGINE=InnoDB;

-- ── 2. Payment_Methods ────────────────────────────────────────
CREATE TABLE Payment_Methods (
  payment_method_id INT         NOT NULL AUTO_INCREMENT,
  method_name       VARCHAR(60) NOT NULL,
  description       VARCHAR(255)         DEFAULT NULL,
  is_active         TINYINT(1)  NOT NULL DEFAULT 1,
  PRIMARY KEY (payment_method_id),
  UNIQUE KEY uq_method_name (method_name)
) ENGINE=InnoDB;

-- ── 3. Fares ──────────────────────────────────────────────────
-- Fixed rate table: zone_from × zone_to → amount (Maloti)
-- Rates:  CBD      → CBD       = M 80.00
--         CBD      → MSU Local = M 120.00
--         MSU Local → CBD      = M 120.00
--         MSU Local → MSU Local = M 150.00
CREATE TABLE Fares (
  fare_id   INT          NOT NULL AUTO_INCREMENT,
  zone_from VARCHAR(40)  NOT NULL,
  zone_to   VARCHAR(40)  NOT NULL,
  amount    DECIMAL(8,2) NOT NULL,
  PRIMARY KEY (fare_id),
  UNIQUE KEY uq_zone_pair (zone_from, zone_to)
) ENGINE=InnoDB;

-- ── 4. Drivers ────────────────────────────────────────────────
CREATE TABLE Drivers (
  driver_id      INT          NOT NULL AUTO_INCREMENT,
  first_name     VARCHAR(60)  NOT NULL,
  last_name      VARCHAR(60)  NOT NULL,
  phone_number   VARCHAR(20)  NOT NULL,
  license_number VARCHAR(30)  NOT NULL,
  vehicle_plate  VARCHAR(15)  NOT NULL,
  vehicle_model  VARCHAR(80)           DEFAULT NULL,
  password_hash  VARCHAR(64)  NOT NULL,
  is_available   TINYINT(1)   NOT NULL DEFAULT 0,
  joined_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (driver_id),
  UNIQUE KEY uq_driver_phone   (phone_number),
  UNIQUE KEY uq_driver_license (license_number),
  UNIQUE KEY uq_driver_plate   (vehicle_plate)
) ENGINE=InnoDB;

-- ── 5. Admin_Users ────────────────────────────────────────────
CREATE TABLE Admin_Users (
  admin_id      INT         NOT NULL AUTO_INCREMENT,
  username      VARCHAR(40) NOT NULL,
  email         VARCHAR(120)NOT NULL,
  password_hash VARCHAR(64) NOT NULL,
  role          VARCHAR(20) NOT NULL DEFAULT 'admin',
  created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (admin_id),
  UNIQUE KEY uq_admin_username (username),
  UNIQUE KEY uq_admin_email    (email)
) ENGINE=InnoDB;

-- ── 6. Rides (CORE) ───────────────────────────────────────────
-- Passenger name + phone are stored inline — no account required.
-- fare_amount is set at booking time from the Fares table.
-- driver_id is NULL until a driver accepts the ride.
CREATE TABLE Rides (
  ride_id             INT          NOT NULL AUTO_INCREMENT,
  passenger_name      VARCHAR(120) NOT NULL,
  passenger_phone     VARCHAR(20)  NOT NULL,
  pickup_location_id  INT          NOT NULL,
  dropoff_location_id INT          NOT NULL,
  driver_id           INT                   DEFAULT NULL,
  payment_method_id   INT          NOT NULL,
  ride_status         VARCHAR(20)  NOT NULL DEFAULT 'REQUESTED',
  requested_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  accepted_at         DATETIME              DEFAULT NULL,
  completed_at        DATETIME              DEFAULT NULL,
  fare_amount         DECIMAL(8,2)          DEFAULT NULL,
  notes               TEXT                  DEFAULT NULL,
  PRIMARY KEY (ride_id),
  -- Enforce pickup ≠ dropoff at DB level
  CONSTRAINT chk_different_locations
    CHECK (pickup_location_id <> dropoff_location_id),
  -- Enforce valid status values
  CONSTRAINT chk_ride_status
    CHECK (ride_status IN ('REQUESTED','ACCEPTED','IN_PROGRESS','COMPLETED','CANCELLED')),
  FOREIGN KEY fk_ride_pickup   (pickup_location_id)  REFERENCES Locations(location_id),
  FOREIGN KEY fk_ride_dropoff  (dropoff_location_id) REFERENCES Locations(location_id),
  FOREIGN KEY fk_ride_driver   (driver_id)           REFERENCES Drivers(driver_id),
  FOREIGN KEY fk_ride_payment  (payment_method_id)   REFERENCES Payment_Methods(payment_method_id),
  -- Indexes for common query patterns
  INDEX idx_ride_status     (ride_status),
  INDEX idx_ride_driver     (driver_id),
  INDEX idx_ride_requested  (requested_at),
  INDEX idx_ride_passenger  (passenger_phone)
) ENGINE=InnoDB;

-- ── 7. Vehicle_Status ─────────────────────────────────────────
-- Audit log of driver availability changes and location updates.
CREATE TABLE Vehicle_Status (
  status_id           INT         NOT NULL AUTO_INCREMENT,
  driver_id           INT         NOT NULL,
  status              VARCHAR(20) NOT NULL DEFAULT 'OFFLINE',
  current_location_id INT                  DEFAULT NULL,
  updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (status_id),
  CONSTRAINT chk_vs_status
    CHECK (status IN ('AVAILABLE','ON_RIDE','OFFLINE')),
  FOREIGN KEY fk_vs_driver   (driver_id)           REFERENCES Drivers(driver_id),
  FOREIGN KEY fk_vs_location (current_location_id) REFERENCES Locations(location_id),
  INDEX idx_vs_driver (driver_id)
) ENGINE=InnoDB;

-- ── 8. Ride_Reports ───────────────────────────────────────────
-- Materialised snapshots generated by admin.
-- total_rides and total_revenue are intentionally denormalised
-- to preserve the state at the time the report was generated.
CREATE TABLE Ride_Reports (
  report_id       INT          NOT NULL AUTO_INCREMENT,
  admin_id        INT          NOT NULL,
  report_type     VARCHAR(60)  NOT NULL DEFAULT 'Daily Summary',
  report_date     DATE         NOT NULL,
  total_rides     INT          NOT NULL DEFAULT 0,
  total_revenue   DECIMAL(10,2)NOT NULL DEFAULT 0.00,
  top_location_id INT                   DEFAULT NULL,
  generated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  notes           TEXT                  DEFAULT NULL,
  PRIMARY KEY (report_id),
  FOREIGN KEY fk_rr_admin    (admin_id)        REFERENCES Admin_Users(admin_id),
  FOREIGN KEY fk_rr_location (top_location_id) REFERENCES Locations(location_id),
  INDEX idx_rr_date (report_date)
) ENGINE=InnoDB;


-- ═══════════════════════════════════════════════════════════════
--  SEED DATA
-- ═══════════════════════════════════════════════════════════════

-- ── Fare rates ────────────────────────────────────────────────
INSERT INTO Fares (zone_from, zone_to, amount) VALUES
  ('CBD',       'CBD',        80.00),
  ('CBD',       'MSU Local', 120.00),
  ('MSU Local', 'CBD',       120.00),
  ('MSU Local', 'MSU Local', 150.00);

-- ── Maseru CBD locations ──────────────────────────────────────
INSERT INTO Locations (location_name, area_zone, description) VALUES
  ('Pioneer Mall',              'CBD',       'Main shopping centre'),
  ('Maseru Bridge',             'CBD West',  'Border crossing'),
  ('Queen II Hospital',         'CBD North', 'Main referral hospital'),
  ('Government Complex',        'CBD',       'Central government offices'),
  ('NUL City Campus',           'CBD East',  'National University of Lesotho'),
  ('CBD Taxi Rank',             'CBD',       'Main transport hub'),
  ('Maseru Central Police',     'CBD',       'Central police station'),
  ('Standard Lesotho Bank',     'CBD',       'Kingsway Road branch'),
  ('Lesotho Post Office',       'CBD',       'Main post office'),
  ('Maseru Railway Station',    'CBD South', 'Railway area'),
  ('Lesotho Sun Hotel',         'CBD North', 'Landmark hotel'),
  ('Sefika Complex',            'CBD',       'Commercial complex'),
  ('Alliance Française Maseru', 'CBD East',  'French cultural centre'),
  ('Lancers Inn',               'CBD',       'CBD hotel'),
  ('Lesotho Bank Tower',        'CBD',       'Financial tower');

-- ── MSU Local villages ────────────────────────────────────────
INSERT INTO Locations (location_name, area_zone, description) VALUES
  ('Ha Abia',      'MSU Local', 'Local village near Maseru'),
  ('Ha Matala',    'MSU Local', 'Local village near Maseru'),
  ('Ha Leqele',    'MSU Local', 'Local village near Maseru'),
  ('Lithabaneng',  'MSU Local', 'Local village near Maseru'),
  ('Ha Pita',      'MSU Local', 'Local village near Maseru'),
  ('Khubetsoana',  'MSU Local', 'Local village near Maseru'),
  ('Naleli',       'MSU Local', 'Local village near Maseru'),
  ('Ha Thetsane',  'MSU Local', 'Local village near Maseru'),
  ('Sea Point',    'MSU Local', 'Local village near Maseru'),
  ('Mohalalitoe',  'MSU Local', 'Local village near Maseru'),
  ('Hills View',   'MSU Local', 'Local village near Maseru');

-- ── Payment methods ───────────────────────────────────────────
INSERT INTO Payment_Methods (method_name, description) VALUES
  ('Cash',             'Physical cash paid directly to driver'),
  ('Mobile Money',     'EcoCash / M-Pesa — recorded only, no gateway'),
  ('Card on Delivery', 'POS card reader with driver');

-- ── Admin account ─────────────────────────────────────────────
-- Password: Admin@1234  (SHA-256)
INSERT INTO Admin_Users (username, email, password_hash, role) VALUES
  ('admin', 'admin@urbancab.co.ls',
   'e3afed0047b08059d0fada10f400c1e5d6d48a2a7b20b0d46a22d18c914c7e3d',
   'superadmin');

-- ── Driver accounts ───────────────────────────────────────────
-- Password for all drivers: Driver@1234  (SHA-256)
INSERT INTO Drivers
  (first_name, last_name, phone_number, license_number,
   vehicle_plate, vehicle_model, password_hash, is_available)
VALUES
  ('Mpho',           'Letsie',   '+26658200001', 'LSO-DL-001',
   'A 123 MS', 'Toyota Corolla 2019',
   '2be793f40d47877af2ae2e7e677dcbda8a1dde9e3bdbb24e5edce9ed3c82ab42', 1),
  ('Retšelisitsoe',  'Tau',      '+26658200002', 'LSO-DL-002',
   'B 456 MS', 'VW Polo 2020',
   '2be793f40d47877af2ae2e7e677dcbda8a1dde9e3bdbb24e5edce9ed3c82ab42', 1),
  ('Selibe',         'Mokhothu', '+26658200003', 'LSO-DL-003',
   'C 789 MS', 'Honda Fit 2018',
   '2be793f40d47877af2ae2e7e677dcbda8a1dde9e3bdbb24e5edce9ed3c82ab42', 0);

-- ── Sample rides ──────────────────────────────────────────────
-- Fares set correctly per zone rules:
--   Pioneer Mall (CBD) → Maseru Bridge (CBD West)  = M 80
--   CBD Taxi Rank (CBD) → Queen II Hospital (CBD North) = M 80
--   Government Complex (CBD) → NUL City Campus (CBD East) = M 80
--   Pioneer Mall (CBD) → Ha Abia (MSU Local) = M 120
INSERT INTO Rides
  (passenger_name, passenger_phone, pickup_location_id, dropoff_location_id,
   driver_id, payment_method_id, ride_status,
   requested_at, accepted_at, completed_at, fare_amount)
VALUES
  ('Thabo Molefe',       '+26657100001', 1,  2, 1, 1, 'COMPLETED',
   '2025-01-10 08:05:00', '2025-01-10 08:07:00', '2025-01-10 08:22:00',  80.00),
  ('Nthabiseng Sithole', '+26657100002', 6,  3, 2, 2, 'COMPLETED',
   '2025-01-10 09:15:00', '2025-01-10 09:17:00', '2025-01-10 09:35:00',  80.00),
  ('Thabo Molefe',       '+26657100001', 4,  5, 1, 1, 'COMPLETED',
   '2025-01-11 07:45:00', '2025-01-11 07:48:00', '2025-01-11 08:00:00',  80.00),
  ('Lerato Mokoena',     '+26657100003', 1, 16, NULL, 1, 'REQUESTED',
   '2025-01-12 11:00:00', NULL, NULL, 120.00);

-- ═══════════════════════════════════════════════════════════════
--  VERIFICATION QUERIES
--  Run these after the script to confirm everything loaded correctly.
-- ═══════════════════════════════════════════════════════════════

-- SELECT 'Tables created:' AS '', COUNT(*) AS count
--   FROM information_schema.tables
--   WHERE table_schema = 'urban_cab_db';
--
-- SELECT 'Locations:' AS '', COUNT(*) FROM Locations;
-- SELECT 'Fares:' AS '', COUNT(*) FROM Fares;
-- SELECT zone_from, zone_to, amount FROM Fares ORDER BY zone_from;
-- SELECT area_zone, COUNT(*) AS count FROM Locations GROUP BY area_zone;
