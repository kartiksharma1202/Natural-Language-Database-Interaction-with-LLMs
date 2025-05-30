-- Create the database
CREATE DATABASE IF NOT EXISTS flask_auth_db;
USE flask_auth_db;

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create grades table
CREATE TABLE grades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    subject VARCHAR(100) NOT NULL,
    score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    grade_letter VARCHAR(2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Insert sample grades (for testing)
-- First, find out what user_id was created
SELECT id FROM users WHERE username = 'your_registered_username';

-- Then use that id in your INSERT statement
iNSERT INTO grades (user_id, subject, score, max_score, grade_letter) VALUES
(1, 'Mathematics', 85, 100, 'B'),
(1, 'Science', 92, 100, 'A'),
(1, 'History', 78, 100, 'C'),
(1, 'English', 88, 100, 'B');