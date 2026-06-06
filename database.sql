-- =========================================
-- LEGACY / UNUSED SCHEMA
-- =========================================
-- This file does not match the live Flask app in database/app.py.
-- Use database/lipalangoang mysql.sql for the working MySQL schema
-- and seed data that support booking, tracking, driver, and admin flows.
-- =========================================

DROP DATABASE IF EXISTS urbancab;
CREATE DATABASE urbancab;
USE urbancab;

-- =========================================
-- TABLE: Users
-- =========================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    employee_no VARCHAR(20) UNIQUE,
    email VARCHAR(100),
    phone VARCHAR(20),
    password VARCHAR(100) NOT NULL,
    role ENUM('admin', 'driver') NOT NULL
);

-- =========================================
-- TABLE: Drivers
-- =========================================
CREATE TABLE drivers (
    driver_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    license_no VARCHAR(50),
    vehicle_reg VARCHAR(50),
    status ENUM('available', 'busy') DEFAULT 'available',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- =========================================
-- TABLE: Locations
-- =========================================
CREATE TABLE locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    area VARCHAR(50)
);

-- =========================================
-- TABLE: Rides
-- =========================================
CREATE TABLE rides (
    ride_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    driver_id INT,
    pickup_location INT,
    dropoff_location INT,
    status ENUM('pending', 'ongoing', 'completed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id),
    FOREIGN KEY (pickup_location) REFERENCES locations(location_id),
    FOREIGN KEY (dropoff_location) REFERENCES locations(location_id)
);

-- =========================================
-- INSERT DATA: Users
-- =========================================
INSERT INTO users (full_name, employee_no, email, phone, password, role) VALUES
('System Admin', 'ADMIN-01', 'admin@urbancab.ls', '58800001', 'UrbanCab@2024', 'admin'),
('Thabo Molapo', 'EN-101', NULL, '58800101', 'UrbanCab@2024', 'driver'),
('Lebo Sebatane', 'EN-102', NULL, '58800102', 'UrbanCab@2024', 'driver'),
('Khotso Letele', 'EN-103', NULL, '58800103', 'UrbanCab@2024', 'driver'),
('Mpho Lerotholi', 'EN-104', NULL, '58800104', 'UrbanCab@2024', 'driver'),
('Neo Mofokeng', 'EN-105', NULL, '58800105', 'UrbanCab@2024', 'driver');

-- =========================================
-- INSERT DATA: Drivers
-- =========================================
INSERT INTO drivers (user_id, license_no, vehicle_reg, status) VALUES
(2, 'L-101', 'A-101', 'available'),
(3, 'L-102', 'A-102', 'available'),
(4, 'L-103', 'A-103', 'available'),
(5, 'L-104', 'A-104', 'available'),
(6, 'L-105', 'A-105', 'available');

-- =========================================
-- INSERT DATA: Locations
-- =========================================
INSERT INTO locations (name, area) VALUES
('Pioneer Mall', 'CBD'),
('Maseru Bridge', 'Border'),
('Queen II', 'North'),
('Pitso Ground', 'East'),
('NUL Roma', 'Roma'),
('Manthabiseng', 'CBD'),
('Sefika Mall', 'CBD'),
('Maseru Mall', 'South');

-- =========================================
-- DONE
-- =========================================
