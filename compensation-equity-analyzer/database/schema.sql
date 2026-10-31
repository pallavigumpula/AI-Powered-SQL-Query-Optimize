-- =============================================================================
-- YottaFlex.ai Compensation Equity Analyzer
-- Database Schema: MySQL 8.0+ Compatible DDL
-- Generated with Foreign Keys, Indexes, and Constraints
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `compensation_equity` 
    DEFAULT CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE `compensation_equity`;

-- Disable foreign key checks during schema creation
SET FOREIGN_KEY_CHECKS = 0;

-- 1. ROLES TABLE
DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
    `id` VARCHAR(50) NOT NULL,
    `code` VARCHAR(20) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `department` VARCHAR(100) NOT NULL,
    `job_family` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_role_code` (`code`),
    KEY `idx_role_department` (`department`),
    KEY `idx_role_job_family` (`job_family`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. LEVELS TABLE
DROP TABLE IF EXISTS `levels`;
CREATE TABLE `levels` (
    `id` VARCHAR(50) NOT NULL,
    `code` VARCHAR(20) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `hierarchy_order` INT NOT NULL,
    `min_experience_years` INT NOT NULL DEFAULT 0,
    `description` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_level_code` (`code`),
    KEY `idx_level_hierarchy` (`hierarchy_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. LOCATIONS TABLE
DROP TABLE IF EXISTS `locations`;
CREATE TABLE `locations` (
    `id` VARCHAR(50) NOT NULL,
    `code` VARCHAR(20) NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `country` VARCHAR(100) NOT NULL,
    `region` VARCHAR(50) NOT NULL,
    `cost_of_living_index` FLOAT NOT NULL DEFAULT 1.0,
    `default_currency` VARCHAR(10) NOT NULL DEFAULT 'USD',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_location_code` (`code`),
    KEY `idx_location_country` (`country`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. COMPENSATION BANDS TABLE
DROP TABLE IF EXISTS `compensation_bands`;
CREATE TABLE `compensation_bands` (
    `id` VARCHAR(100) NOT NULL,
    `role_id` VARCHAR(50) NOT NULL,
    `level_id` VARCHAR(50) NOT NULL,
    `location_id` VARCHAR(50) NOT NULL,
    `currency` VARCHAR(10) NOT NULL DEFAULT 'USD',
    `min_salary` FLOAT NOT NULL,
    `mid_salary` FLOAT NOT NULL,
    `max_salary` FLOAT NOT NULL,
    `effective_from` DATE NOT NULL,
    `effective_to` DATE NOT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_band_role` (`role_id`),
    KEY `idx_band_level` (`level_id`),
    KEY `idx_band_location` (`location_id`),
    KEY `idx_band_dates` (`effective_from`, `effective_to`),
    CONSTRAINT `fk_band_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_band_level` FOREIGN KEY (`level_id`) REFERENCES `levels` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_band_location` FOREIGN KEY (`location_id`) REFERENCES `locations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. EMPLOYEES TABLE
DROP TABLE IF EXISTS `employees`;
CREATE TABLE `employees` (
    `id` VARCHAR(50) NOT NULL,
    `first_name` VARCHAR(100) NOT NULL,
    `last_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL,
    `department` VARCHAR(100) NOT NULL,
    `role_id` VARCHAR(50) NOT NULL,
    `level_id` VARCHAR(50) NOT NULL,
    `location_id` VARCHAR(50) NOT NULL,
    `manager_id` VARCHAR(50) DEFAULT NULL,
    `hire_date` DATE NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'Active',
    `fte` FLOAT NOT NULL DEFAULT 1.0,
    `currency` VARCHAR(10) NOT NULL DEFAULT 'USD',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_employee_email` (`email`),
    KEY `idx_emp_role` (`role_id`),
    KEY `idx_emp_level` (`level_id`),
    KEY `idx_emp_location` (`location_id`),
    KEY `idx_emp_manager` (`manager_id`),
    KEY `idx_emp_hire_date` (`hire_date`),
    CONSTRAINT `fk_emp_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`),
    CONSTRAINT `fk_emp_level` FOREIGN KEY (`level_id`) REFERENCES `levels` (`id`),
    CONSTRAINT `fk_emp_location` FOREIGN KEY (`location_id`) REFERENCES `locations` (`id`),
    CONSTRAINT `fk_emp_manager` FOREIGN KEY (`manager_id`) REFERENCES `employees` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. SALARY RECORDS TABLE
DROP TABLE IF EXISTS `salary_records`;
CREATE TABLE `salary_records` (
    `id` VARCHAR(100) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `band_id` VARCHAR(100) DEFAULT NULL,
    `amount` FLOAT NOT NULL,
    `currency` VARCHAR(10) NOT NULL DEFAULT 'USD',
    `effective_date` DATE NOT NULL,
    `fte` FLOAT NOT NULL DEFAULT 1.0,
    `normalized_salary` FLOAT DEFAULT NULL,
    `compa_ratio` FLOAT DEFAULT NULL,
    `within_band_position` FLOAT DEFAULT NULL,
    `band_status` VARCHAR(30) NOT NULL DEFAULT 'WITHIN_BAND',
    `is_current` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_sal_employee` (`employee_id`),
    KEY `idx_sal_band` (`band_id`),
    KEY `idx_sal_effective_date` (`effective_date`),
    KEY `idx_sal_is_current` (`is_current`),
    CONSTRAINT `fk_sal_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_sal_band` FOREIGN KEY (`band_id`) REFERENCES `compensation_bands` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. PERFORMANCE EVIDENCES TABLE
DROP TABLE IF EXISTS `performance_evidences`;
CREATE TABLE `performance_evidences` (
    `id` VARCHAR(100) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `review_cycle` VARCHAR(20) NOT NULL,
    `rating` INT NOT NULL,
    `goal_completion_percentage` FLOAT NOT NULL DEFAULT 100.0,
    `evidence_summary` TEXT,
    `reviewer_id` VARCHAR(50) DEFAULT NULL,
    `review_date` DATE NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_perf_employee` (`employee_id`),
    KEY `idx_perf_cycle` (`review_cycle`),
    CONSTRAINT `fk_perf_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_perf_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `employees` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. TENURES TABLE
DROP TABLE IF EXISTS `tenures`;
CREATE TABLE `tenures` (
    `id` VARCHAR(50) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `total_months_experience` INT NOT NULL DEFAULT 0,
    `company_tenure_months` INT NOT NULL DEFAULT 0,
    `role_tenure_months` INT NOT NULL DEFAULT 0,
    `prior_experience_months` INT NOT NULL DEFAULT 0,
    `last_calculated_date` DATE NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tenure_employee` (`employee_id`),
    CONSTRAINT `fk_tenure_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. PROMOTIONS TABLE
DROP TABLE IF EXISTS `promotions`;
CREATE TABLE `promotions` (
    `id` VARCHAR(50) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `from_level_id` VARCHAR(50) NOT NULL,
    `to_level_id` VARCHAR(50) NOT NULL,
    `effective_date` DATE NOT NULL,
    `justification` TEXT NOT NULL,
    `salary_increase_pct` FLOAT DEFAULT NULL,
    `approved_by` VARCHAR(50) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_prom_employee` (`employee_id`),
    KEY `idx_prom_dates` (`effective_date`),
    CONSTRAINT `fk_prom_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prom_from_level` FOREIGN KEY (`from_level_id`) REFERENCES `levels` (`id`),
    CONSTRAINT `fk_prom_to_level` FOREIGN KEY (`to_level_id`) REFERENCES `levels` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. ADJUSTMENT PROPOSALS TABLE
DROP TABLE IF EXISTS `adjustment_proposals`;
CREATE TABLE `adjustment_proposals` (
    `id` VARCHAR(50) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `current_salary` FLOAT NOT NULL,
    `proposed_salary` FLOAT NOT NULL,
    `currency` VARCHAR(10) NOT NULL DEFAULT 'USD',
    `percentage_change` FLOAT NOT NULL,
    `reason` VARCHAR(200) NOT NULL,
    `supporting_evidence` TEXT NOT NULL,
    `status` VARCHAR(50) NOT NULL DEFAULT 'Draft',
    `priority` VARCHAR(20) NOT NULL DEFAULT 'Medium',
    `submitted_by` VARCHAR(100) DEFAULT NULL,
    `submitted_at` DATETIME DEFAULT NULL,
    `reviewed_by` VARCHAR(100) DEFAULT NULL,
    `reviewed_at` DATETIME DEFAULT NULL,
    `effective_date` DATE NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_adj_employee` (`employee_id`),
    KEY `idx_adj_status` (`status`),
    CONSTRAINT `fk_adj_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. USERS TABLE
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` VARCHAR(50) NOT NULL,
    `username` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `role` VARCHAR(50) NOT NULL,
    `employee_id` VARCHAR(50) DEFAULT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_username` (`username`),
    UNIQUE KEY `uk_user_email` (`email`),
    KEY `idx_user_role` (`role`),
    CONSTRAINT `fk_user_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. CURRENCY EXCHANGE RATES TABLE
DROP TABLE IF EXISTS `currency_exchange_rates`;
CREATE TABLE `currency_exchange_rates` (
    `id` VARCHAR(50) NOT NULL,
    `from_currency` VARCHAR(10) NOT NULL,
    `to_currency` VARCHAR(10) NOT NULL,
    `rate` FLOAT NOT NULL,
    `effective_from` DATE NOT NULL,
    `effective_to` DATE NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_fx_currencies` (`from_currency`, `to_currency`),
    KEY `idx_fx_dates` (`effective_from`, `effective_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. APPROVAL HISTORY TABLE
DROP TABLE IF EXISTS `approval_history`;
CREATE TABLE `approval_history` (
    `id` VARCHAR(50) NOT NULL,
    `proposal_id` VARCHAR(50) NOT NULL,
    `previous_status` VARCHAR(50) NOT NULL,
    `new_status` VARCHAR(50) NOT NULL,
    `actor_id` VARCHAR(100) NOT NULL,
    `actor_role` VARCHAR(50) NOT NULL,
    `action_type` VARCHAR(50) NOT NULL,
    `comments` TEXT,
    `action_timestamp` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_apph_proposal` (`proposal_id`),
    CONSTRAINT `fk_apph_proposal` FOREIGN KEY (`proposal_id`) REFERENCES `adjustment_proposals` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. ADJUSTMENT EVENTS TABLE
DROP TABLE IF EXISTS `adjustment_events`;
CREATE TABLE `adjustment_events` (
    `id` VARCHAR(50) NOT NULL,
    `proposal_id` VARCHAR(50) DEFAULT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `old_salary` FLOAT NOT NULL,
    `new_salary` FLOAT NOT NULL,
    `effective_date` DATE NOT NULL,
    `is_authorized` TINYINT(1) NOT NULL DEFAULT 1,
    `applied_by` VARCHAR(100) NOT NULL,
    `notes` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_event_employee` (`employee_id`),
    KEY `idx_event_proposal` (`proposal_id`),
    CONSTRAINT `fk_event_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_event_proposal` FOREIGN KEY (`proposal_id`) REFERENCES `adjustment_proposals` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. AUDIT LOGS TABLE
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
    `id` VARCHAR(50) NOT NULL,
    `entity_name` VARCHAR(50) NOT NULL,
    `entity_id` VARCHAR(100) NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `actor_id` VARCHAR(100) NOT NULL,
    `actor_role` VARCHAR(50) NOT NULL,
    `old_values` TEXT,
    `new_values` TEXT,
    `ip_address` VARCHAR(50) DEFAULT NULL,
    `severity` VARCHAR(20) NOT NULL DEFAULT 'INFO',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_audit_entity` (`entity_name`, `entity_id`),
    KEY `idx_audit_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. COMPARISON GROUPS TABLE
DROP TABLE IF EXISTS `comparison_groups`;
CREATE TABLE `comparison_groups` (
    `id` VARCHAR(50) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `role_id` VARCHAR(50) DEFAULT NULL,
    `level_id` VARCHAR(50) DEFAULT NULL,
    `location_id` VARCHAR(50) DEFAULT NULL,
    `rationale` TEXT NOT NULL,
    `is_valid` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_cgroup_role` (`role_id`),
    CONSTRAINT `fk_cgroup_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. COMPARISON GROUP MEMBERS TABLE (BRIDGE TABLE)
DROP TABLE IF EXISTS `comparison_group_members`;
CREATE TABLE `comparison_group_members` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `comparison_group_id` VARCHAR(50) NOT NULL,
    `employee_id` VARCHAR(50) NOT NULL,
    `joined_date` DATE NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cgroup_member` (`comparison_group_id`, `employee_id`),
    KEY `idx_cgm_employee` (`employee_id`),
    CONSTRAINT `fk_cgm_group` FOREIGN KEY (`comparison_group_id`) REFERENCES `comparison_groups` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cgm_employee` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. DATA QUALITY ISSUES TABLE
DROP TABLE IF EXISTS `data_quality_issues`;
CREATE TABLE `data_quality_issues` (
    `id` VARCHAR(50) NOT NULL,
    `issue_type` VARCHAR(50) NOT NULL,
    `severity` VARCHAR(20) NOT NULL DEFAULT 'HIGH',
    `entity_type` VARCHAR(50) NOT NULL,
    `entity_id` VARCHAR(100) NOT NULL,
    `description` TEXT NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    `ground_truth_label` VARCHAR(50) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` DATETIME DEFAULT NULL,
    `resolution_notes` TEXT,
    PRIMARY KEY (`id`),
    KEY `idx_dqi_type` (`issue_type`),
    KEY `idx_dqi_status` (`status`),
    KEY `idx_dqi_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;
