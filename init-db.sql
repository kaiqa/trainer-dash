-- Database initialization script for MySQL
-- This runs automatically when the MySQL container starts for the first time

-- Create database if not exists (handled by MYSQL_DATABASE env var)
-- USE meetings_db;

-- Create meetings table (legacy)
CREATE TABLE IF NOT EXISTS `meetings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_name` VARCHAR(255) NOT NULL,
    `user_email` VARCHAR(255) NOT NULL,
    `meeting_time` DATETIME NOT NULL,
    `meeting_duration` INT NOT NULL DEFAULT 30,
    `company_name` VARCHAR(255) NULL,
    `job_opportunity` TEXT NULL,
    `recruiter_name` VARCHAR(255) NULL,
    `is_active` BOOLEAN DEFAULT TRUE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    INDEX `ix_meetings_user_name` (`user_name`),
    INDEX `ix_meetings_user_email` (`user_email`),
    INDEX `ix_meetings_meeting_time` (`meeting_time`),
    INDEX `ix_meetings_is_active` (`is_active`),
    INDEX `ix_meetings_active_created` (`is_active`, `created_at`),
    INDEX `ix_meetings_email_active` (`user_email`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create trainings table
CREATE TABLE IF NOT EXISTS `trainings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_name` VARCHAR(255) NOT NULL,
    `time_spent_minutes` INT NOT NULL,
    `training_date` DATE NOT NULL,
    `training_time` TIME NOT NULL,
    `type` VARCHAR(100) NOT NULL,
    `sets` INT NOT NULL,
    `repetitions` INT NOT NULL,
    `weight` INT NULL,
    `body_type` VARCHAR(100) NOT NULL,
    `injuries` VARCHAR(10) NOT NULL DEFAULT 'no',
    `pain` VARCHAR(10) NOT NULL DEFAULT 'no',
    `pain_source` VARCHAR(255) NULL,
    `rating` INT NULL,
    `session_notes` TEXT NULL,
    `status` ENUM('planned', 'done', 'skipped') DEFAULT 'planned' NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    INDEX `ix_trainings_user_name` (`user_name`),
    INDEX `ix_trainings_training_date` (`training_date`),
    INDEX `ix_trainings_type` (`type`),
    INDEX `ix_trainings_body_type` (`body_type`),
    INDEX `ix_trainings_status` (`status`),
    INDEX `ix_trainings_status_created` (`status`, `created_at`),
    INDEX `ix_trainings_user_date` (`user_name`, `training_date`),
    INDEX `ix_trainings_body_type_date` (`body_type`, `training_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create settings table
CREATE TABLE IF NOT EXISTS `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) NOT NULL,
    `value` TEXT NOT NULL,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY `uq_settings_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default settings (only if not exist)
INSERT IGNORE INTO `settings` (`key`, `value`, `description`) VALUES
('webhook_host', '0.0.0.0', 'IP address to bind webhook server'),
('webhook_port', '5687', 'Port for webhook server'),
('webhook_path', '/webhook/req-meeting', 'Webhook endpoint path for meetings'),
('training_webhook_path', '/webhook/record-training', 'Webhook endpoint path for training');

-- Grant permissions (if using specific user)
-- GRANT ALL PRIVILEGES ON meetings_db.* TO 'meetings_user'@'%';
-- FLUSH PRIVILEGES;