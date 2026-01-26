-- ============================================================================
-- MoMo SMS Data Processing System - Database Setup Script
-- Version: 1.0
-- Description: Complete database schema for MTN Mobile Money SMS transaction processing
-- ============================================================================

DROP DATABASE IF EXISTS momo_sms_db;
CREATE DATABASE momo_sms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE momo_sms_db;

-- ============================================================================
-- TABLE: users
-- Description: Stores information about all parties involved in transactions
-- ============================================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique identifier for each user',
    full_name VARCHAR(100) NOT NULL COMMENT 'Full name of the user',
    phone_number VARCHAR(15) COMMENT 'Complete phone number (when available)',
    masked_phone VARCHAR(15) COMMENT 'Masked phone number from SMS (e.g., *********013)',
    account_number VARCHAR(20) COMMENT 'MoMo account number',
    user_type ENUM('individual', 'merchant', 'service', 'agent') DEFAULT 'individual' COMMENT 'Type of user account',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the user account is active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    CONSTRAINT chk_phone_format CHECK (phone_number IS NULL OR phone_number REGEXP '^[0-9]{9,15}$'),
    CONSTRAINT chk_name_length CHECK (LENGTH(full_name) >= 2)
) ENGINE=InnoDB COMMENT='User/Customer information for transaction parties';

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_name ON users(full_name);
CREATE INDEX idx_users_account ON users(account_number);

-- ============================================================================
-- TABLE: transaction_categories
-- Description: Defines types of mobile money transactions
-- ============================================================================
CREATE TABLE transaction_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique identifier for category',
    category_name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Human-readable category name',
    category_code VARCHAR(10) COMMENT 'SMS prefix code (e.g., *165*, *113*)',
    description TEXT COMMENT 'Detailed description of the transaction type',
    is_debit BOOLEAN DEFAULT TRUE COMMENT 'TRUE if money leaves account, FALSE if money enters',
    fee_applicable BOOLEAN DEFAULT TRUE COMMENT 'Whether fees typically apply to this category',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    
    CONSTRAINT chk_category_name CHECK (LENGTH(category_name) >= 3)
) ENGINE=InnoDB COMMENT='Transaction type classification';

CREATE INDEX idx_category_code ON transaction_categories(category_code);

-- ============================================================================
-- TABLE: transactions
-- Description: Main transaction records parsed from SMS messages
-- ============================================================================
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Internal unique identifier',
    external_txn_id VARCHAR(20) COMMENT 'Transaction ID from MoMo system (TxId/Financial Transaction Id)',
    category_id INT NOT NULL COMMENT 'Foreign key to transaction category',
    amount DECIMAL(15, 2) NOT NULL COMMENT 'Transaction amount in RWF',
    fee DECIMAL(10, 2) DEFAULT 0.00 COMMENT 'Transaction fee charged',
    balance_after DECIMAL(15, 2) COMMENT 'Account balance after transaction',
    currency VARCHAR(3) DEFAULT 'RWF' COMMENT 'Currency code',
    transaction_timestamp DATETIME NOT NULL COMMENT 'When the transaction occurred',
    sender_message TEXT COMMENT 'Optional message from sender',
    merchant_code VARCHAR(10) COMMENT 'Merchant code for merchant payments',
    status ENUM('completed', 'pending', 'failed', 'reversed') DEFAULT 'completed' COMMENT 'Transaction status',
    raw_sms_id INT COMMENT 'Reference to original SMS data',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    
    CONSTRAINT fk_transaction_category FOREIGN KEY (category_id) 
        REFERENCES transaction_categories(category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_positive_amount CHECK (amount > 0),
    CONSTRAINT chk_non_negative_fee CHECK (fee >= 0),
    CONSTRAINT chk_currency CHECK (currency IN ('RWF', 'USD', 'EUR'))
) ENGINE=InnoDB COMMENT='Main transaction records from MoMo SMS';

CREATE INDEX idx_txn_external_id ON transactions(external_txn_id);
CREATE INDEX idx_txn_timestamp ON transactions(transaction_timestamp);
CREATE INDEX idx_txn_category ON transactions(category_id);
CREATE INDEX idx_txn_amount ON transactions(amount);
CREATE INDEX idx_txn_status ON transactions(status);

-- ============================================================================
-- TABLE: transaction_parties (Junction Table - Resolves M:N relationship)
-- Description: Links users to transactions with their roles (sender/receiver)
-- One transaction can have multiple parties, one user can be in many transactions
-- ============================================================================
CREATE TABLE transaction_parties (
    party_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique identifier',
    transaction_id INT NOT NULL COMMENT 'Foreign key to transaction',
    user_id INT NOT NULL COMMENT 'Foreign key to user',
    party_role ENUM('sender', 'receiver', 'merchant', 'agent', 'service_provider') NOT NULL COMMENT 'Role of user in transaction',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    
    CONSTRAINT fk_party_transaction FOREIGN KEY (transaction_id) 
        REFERENCES transactions(transaction_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_party_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_transaction_party_role UNIQUE (transaction_id, user_id, party_role)
) ENGINE=InnoDB COMMENT='Junction table linking users to transactions with roles (M:N resolution)';

CREATE INDEX idx_party_transaction ON transaction_parties(transaction_id);
CREATE INDEX idx_party_user ON transaction_parties(user_id);
CREATE INDEX idx_party_role ON transaction_parties(party_role);

-- ============================================================================
-- TABLE: system_logs
-- Description: Audit trail for data processing operations
-- ============================================================================
CREATE TABLE system_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique log entry identifier',
    log_type ENUM('import', 'export', 'error', 'processing', 'audit', 'security') NOT NULL COMMENT 'Type of log entry',
    log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO' COMMENT 'Severity level',
    message TEXT NOT NULL COMMENT 'Log message details',
    affected_table VARCHAR(50) COMMENT 'Table affected by operation',
    affected_records INT DEFAULT 0 COMMENT 'Number of records affected',
    execution_time_ms INT COMMENT 'Operation execution time in milliseconds',
    ip_address VARCHAR(45) COMMENT 'IP address of client (supports IPv6)',
    user_agent VARCHAR(255) COMMENT 'User agent or system identifier',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Log entry timestamp',
    created_by VARCHAR(50) COMMENT 'User or process that created the log',
    
    CONSTRAINT chk_affected_records CHECK (affected_records >= 0)
) ENGINE=InnoDB COMMENT='System audit and processing logs';

CREATE INDEX idx_log_type ON system_logs(log_type);
CREATE INDEX idx_log_level ON system_logs(log_level);
CREATE INDEX idx_log_timestamp ON system_logs(created_at);
CREATE INDEX idx_log_table ON system_logs(affected_table);

-- ============================================================================
-- TABLE: sms_raw_data
-- Description: Stores original SMS data for audit and reprocessing
-- ============================================================================
CREATE TABLE sms_raw_data (
    sms_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique SMS record identifier',
    protocol VARCHAR(10) COMMENT 'SMS protocol',
    address VARCHAR(50) NOT NULL COMMENT 'Sender address (e.g., M-Money)',
    sms_date_ms BIGINT COMMENT 'SMS date in milliseconds (original format)',
    sms_type INT COMMENT 'SMS type code',
    body TEXT NOT NULL COMMENT 'Full SMS body text',
    service_center VARCHAR(20) COMMENT 'Service center number',
    date_sent_ms BIGINT COMMENT 'Date sent in milliseconds',
    readable_date VARCHAR(50) COMMENT 'Human-readable date string',
    contact_name VARCHAR(100) COMMENT 'Contact name if available',
    is_processed BOOLEAN DEFAULT FALSE COMMENT 'Whether SMS has been parsed into transaction',
    processing_error TEXT COMMENT 'Error message if processing failed',
    transaction_id INT COMMENT 'Linked transaction after processing',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Import timestamp',
    
    CONSTRAINT fk_sms_transaction FOREIGN KEY (transaction_id) 
        REFERENCES transactions(transaction_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Raw SMS data storage for audit trail';

CREATE INDEX idx_sms_address ON sms_raw_data(address);
CREATE INDEX idx_sms_processed ON sms_raw_data(is_processed);
CREATE INDEX idx_sms_date ON sms_raw_data(sms_date_ms);

-- ============================================================================
-- TABLE: balance_history
-- Description: Tracks account balance changes over time
-- ============================================================================
CREATE TABLE balance_history (
    balance_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique identifier',
    user_id INT NOT NULL COMMENT 'Account owner',
    transaction_id INT COMMENT 'Transaction that caused balance change',
    balance_before DECIMAL(15, 2) COMMENT 'Balance before transaction',
    balance_after DECIMAL(15, 2) NOT NULL COMMENT 'Balance after transaction',
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When balance was recorded',
    
    CONSTRAINT fk_balance_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_balance_transaction FOREIGN KEY (transaction_id) 
        REFERENCES transactions(transaction_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_balance_non_negative CHECK (balance_after >= 0)
) ENGINE=InnoDB COMMENT='Historical record of account balances';

CREATE INDEX idx_balance_user ON balance_history(user_id);
CREATE INDEX idx_balance_timestamp ON balance_history(recorded_at);

-- ============================================================================
-- TABLE: user_tags (Additional M:N example - Users can have multiple tags)
-- Description: Flexible tagging system for user categorization
-- ============================================================================
CREATE TABLE tags (
    tag_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique tag identifier',
    tag_name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Tag name',
    tag_description VARCHAR(255) COMMENT 'Tag description',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp'
) ENGINE=InnoDB COMMENT='Available tags for user categorization';

CREATE TABLE user_tags (
    user_tag_id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique identifier',
    user_id INT NOT NULL COMMENT 'Foreign key to user',
    tag_id INT NOT NULL COMMENT 'Foreign key to tag',
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When tag was assigned',
    assigned_by VARCHAR(50) COMMENT 'Who assigned the tag',
    
    CONSTRAINT fk_usertag_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_usertag_tag FOREIGN KEY (tag_id) 
        REFERENCES tags(tag_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_user_tag UNIQUE (user_id, tag_id)
) ENGINE=InnoDB COMMENT='Junction table for user-tag M:N relationship';

-- ============================================================================
-- SAMPLE DATA INSERTION (DML)
-- ============================================================================

-- Insert Transaction Categories
INSERT INTO transaction_categories (category_name, category_code, description, is_debit, fee_applicable) VALUES
('Incoming Transfer', NULL, 'Money received from another MoMo user (P2P incoming)', FALSE, FALSE),
('Outgoing Transfer', '*165*', 'Money sent to another MoMo user (P2P outgoing)', TRUE, TRUE),
('Merchant Payment', NULL, 'Payment to a registered merchant', TRUE, FALSE),
('Bank Deposit', '*113*', 'Cash deposited via bank or agent', FALSE, FALSE),
('Airtime Purchase', '*162*', 'Mobile airtime top-up', TRUE, FALSE),
('Bundle Purchase', '*162*', 'Data or voice bundle purchase', TRUE, FALSE),
('Data Bundle', '*164*', 'Internet data bundle subscription', TRUE, FALSE),
('Cash Withdrawal', '*165*', 'Cash withdrawn from agent', TRUE, TRUE);

-- Insert Users
INSERT INTO users (full_name, phone_number, masked_phone, account_number, user_type) VALUES
('System Owner', '250795963036', NULL, '36521838', 'individual'),
('Jane Smith', '250790777777', '*********013', NULL, 'individual'),
('Samuel Carter', '250791666666', NULL, NULL, 'individual'),
('Robert Brown', '250788999999', NULL, NULL, 'individual'),
('Linda Green', '250790777777', NULL, NULL, 'individual'),
('Alex Doe', '250791666666', NULL, NULL, 'individual'),
('MTN Airtime', NULL, NULL, NULL, 'service'),
('Data Bundle MTN', NULL, NULL, NULL, 'service');

-- Insert Transactions
INSERT INTO transactions (external_txn_id, category_id, amount, fee, balance_after, transaction_timestamp, merchant_code, status) VALUES
('76662021700', 1, 2000.00, 0.00, 2000.00, '2024-05-10 16:30:51', NULL, 'completed'),
('73214484437', 3, 1000.00, 0.00, 1000.00, '2024-05-10 16:31:39', '12845', 'completed'),
('51732411227', 3, 600.00, 0.00, 400.00, '2024-05-10 21:32:32', '95464', 'completed'),
(NULL, 4, 40000.00, 0.00, 40400.00, '2024-05-11 18:43:49', NULL, 'completed'),
('17818959211', 3, 2000.00, 0.00, 38400.00, '2024-05-11 18:48:42', '14965', 'completed'),
(NULL, 2, 10000.00, 100.00, 28300.00, '2024-05-11 20:34:47', NULL, 'completed'),
('13913173274', 5, 2000.00, 0.00, 25280.00, '2024-05-12 11:41:28', NULL, 'completed'),
('18087757600', 7, 10000.00, 0.00, 88000.00, '2025-01-14 17:29:36', NULL, 'completed');

-- Insert Transaction Parties (Junction Table Data)
INSERT INTO transaction_parties (transaction_id, user_id, party_role) VALUES
(1, 1, 'receiver'),
(1, 2, 'sender'),
(2, 1, 'sender'),
(2, 2, 'merchant'),
(3, 1, 'sender'),
(3, 3, 'merchant'),
(4, 1, 'receiver'),
(5, 1, 'sender'),
(5, 3, 'merchant'),
(6, 1, 'sender'),
(6, 3, 'receiver'),
(7, 1, 'sender'),
(7, 7, 'service_provider'),
(8, 1, 'sender'),
(8, 8, 'service_provider');

-- Insert System Logs
INSERT INTO system_logs (log_type, log_level, message, affected_table, affected_records, execution_time_ms, created_by) VALUES
('import', 'INFO', 'Started XML import process for MoMo SMS backup', 'sms_raw_data', 0, NULL, 'data_processor'),
('processing', 'INFO', 'Parsed incoming transfer SMS successfully', 'transactions', 1, 45, 'sms_parser'),
('processing', 'INFO', 'Parsed merchant payment SMS successfully', 'transactions', 1, 38, 'sms_parser'),
('import', 'INFO', 'Completed XML import: 1693 SMS records loaded', 'sms_raw_data', 1693, 5230, 'data_processor'),
('audit', 'INFO', 'Daily transaction summary generated', 'transactions', 156, 890, 'report_generator'),
('error', 'WARNING', 'Failed to parse SMS: unrecognized format', 'sms_raw_data', 1, NULL, 'sms_parser'),
('security', 'INFO', 'User authentication successful', NULL, 0, NULL, 'auth_service');

-- Insert Sample Raw SMS Data
INSERT INTO sms_raw_data (protocol, address, sms_date_ms, sms_type, body, service_center, date_sent_ms, readable_date, is_processed, transaction_id) VALUES
('0', 'M-Money', 1715351458724, 1, 'You have received 2000 RWF from Jane Smith (*********013) on your mobile money account at 2024-05-10 16:30:51. Message from sender: . Your new balance:2000 RWF. Financial Transaction Id: 76662021700.', '+250788110381', 1715351451000, '10 May 2024 4:30:58 PM', TRUE, 1),
('0', 'M-Money', 1715351506754, 1, 'TxId: 73214484437. Your payment of 1,000 RWF to Jane Smith 12845 has been completed at 2024-05-10 16:31:39. Your new balance: 1,000 RWF. Fee was 0 RWF.', '+250788110381', 1715351498000, '10 May 2024 4:31:46 PM', TRUE, 2),
('0', 'M-Money', 1715445936412, 1, '*113*R*A bank deposit of 40000 RWF has been added to your mobile money account at 2024-05-11 18:43:49. Your NEW BALANCE :40400 RWF. Cash Deposit::CASH::::0::250795963036.Thank you for using MTN MobileMoney.*EN#', '+250788110381', 1715445829000, '11 May 2024 6:45:36 PM', TRUE, 4),
('0', 'M-Money', 1715452495316, 1, '*165*S*10000 RWF transferred to Samuel Carter (250791666666) from 36521838 at 2024-05-11 20:34:47 . Fee was: 100 RWF. New balance: 28300 RWF.', '+250788110381', 1715452487000, '11 May 2024 8:34:55 PM', TRUE, 6),
('0', 'M-Money', 1715506895734, 1, '*162*TxId:13913173274*S*Your payment of 2000 RWF to Airtime with token  has been completed at 2024-05-12 11:41:28. Fee was 0 RWF. Your new balance: 25280 RWF . Message: - -.', '+250788110381', 1715506888000, '12 May 2024 11:41:35 AM', TRUE, 7);

-- Insert Tags
INSERT INTO tags (tag_name, tag_description) VALUES
('frequent_sender', 'User sends money frequently'),
('frequent_receiver', 'User receives money frequently'),
('high_value', 'User involved in high-value transactions'),
('merchant_partner', 'Registered merchant partner'),
('vip', 'VIP customer status');

-- Insert User Tags
INSERT INTO user_tags (user_id, tag_id, assigned_by) VALUES
(1, 1, 'system'),
(1, 3, 'system'),
(2, 2, 'system'),
(2, 5, 'admin'),
(3, 2, 'system'),
(4, 4, 'admin'),
(7, 4, 'system');

-- Insert Balance History
INSERT INTO balance_history (user_id, transaction_id, balance_before, balance_after) VALUES
(1, 1, 0.00, 2000.00),
(1, 2, 2000.00, 1000.00),
(1, 3, 1000.00, 400.00),
(1, 4, 400.00, 40400.00),
(1, 5, 40400.00, 38400.00),
(1, 6, 38400.00, 28300.00),
(1, 7, 28300.00, 25280.00);

-- ============================================================================
-- SECURITY RULES AND CONSTRAINTS
-- ============================================================================

-- Create a view to mask sensitive data for reports
CREATE VIEW v_transactions_masked AS
SELECT 
    t.transaction_id,
    t.external_txn_id,
    tc.category_name,
    t.amount,
    t.fee,
    t.balance_after,
    t.transaction_timestamp,
    t.status,
    CONCAT(LEFT(u_sender.full_name, 1), '****') AS sender_masked,
    CONCAT(LEFT(u_receiver.full_name, 1), '****') AS receiver_masked
FROM transactions t
JOIN transaction_categories tc ON t.category_id = tc.category_id
LEFT JOIN transaction_parties tp_sender ON t.transaction_id = tp_sender.transaction_id AND tp_sender.party_role = 'sender'
LEFT JOIN users u_sender ON tp_sender.user_id = u_sender.user_id
LEFT JOIN transaction_parties tp_receiver ON t.transaction_id = tp_receiver.transaction_id AND tp_receiver.party_role IN ('receiver', 'merchant', 'service_provider')
LEFT JOIN users u_receiver ON tp_receiver.user_id = u_receiver.user_id;

-- Create a view for daily transaction summaries
CREATE VIEW v_daily_summary AS
SELECT 
    DATE(transaction_timestamp) AS transaction_date,
    tc.category_name,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    SUM(fee) AS total_fees,
    AVG(amount) AS avg_amount
FROM transactions t
JOIN transaction_categories tc ON t.category_id = tc.category_id
GROUP BY DATE(transaction_timestamp), tc.category_name;

-- ============================================================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- ============================================================================

DELIMITER //

-- Procedure to get user transaction history
CREATE PROCEDURE sp_get_user_transactions(IN p_user_id INT)
BEGIN
    SELECT 
        t.transaction_id,
        t.external_txn_id,
        tc.category_name,
        tp.party_role,
        t.amount,
        t.fee,
        t.balance_after,
        t.transaction_timestamp,
        t.status
    FROM transactions t
    JOIN transaction_categories tc ON t.category_id = tc.category_id
    JOIN transaction_parties tp ON t.transaction_id = tp.transaction_id
    WHERE tp.user_id = p_user_id
    ORDER BY t.transaction_timestamp DESC;
END //

-- Procedure to log system events
CREATE PROCEDURE sp_log_event(
    IN p_log_type ENUM('import', 'export', 'error', 'processing', 'audit', 'security'),
    IN p_log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
    IN p_message TEXT,
    IN p_affected_table VARCHAR(50),
    IN p_affected_records INT,
    IN p_created_by VARCHAR(50)
)
BEGIN
    INSERT INTO system_logs (log_type, log_level, message, affected_table, affected_records, created_by)
    VALUES (p_log_type, p_log_level, p_message, p_affected_table, p_affected_records, p_created_by);
END //

-- Trigger to log transaction insertions
CREATE TRIGGER trg_after_transaction_insert
AFTER INSERT ON transactions
FOR EACH ROW
BEGIN
    INSERT INTO system_logs (log_type, log_level, message, affected_table, affected_records, created_by)
    VALUES ('audit', 'INFO', CONCAT('New transaction created: ID=', NEW.transaction_id, ', Amount=', NEW.amount), 'transactions', 1, 'system_trigger');
END //

-- Trigger to prevent negative balances in history
CREATE TRIGGER trg_before_balance_insert
BEFORE INSERT ON balance_history
FOR EACH ROW
BEGIN
    IF NEW.balance_after < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Balance cannot be negative';
    END IF;
END //

DELIMITER ;

-- ============================================================================
-- SAMPLE QUERIES FOR TESTING (CRUD OPERATIONS)
-- ============================================================================

-- READ: Get all transactions with category names
SELECT t.*, tc.category_name 
FROM transactions t 
JOIN transaction_categories tc ON t.category_id = tc.category_id
LIMIT 10;

-- READ: Get transaction summary by category
SELECT 
    tc.category_name,
    COUNT(*) as total_transactions,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount
FROM transactions t
JOIN transaction_categories tc ON t.category_id = tc.category_id
GROUP BY tc.category_name;

-- READ: Get all parties involved in a specific transaction
SELECT 
    t.transaction_id,
    t.amount,
    u.full_name,
    tp.party_role
FROM transactions t
JOIN transaction_parties tp ON t.transaction_id = tp.transaction_id
JOIN users u ON tp.user_id = u.user_id
WHERE t.transaction_id = 1;

-- READ: Get user's transaction history with running balance
SELECT 
    t.transaction_timestamp,
    tc.category_name,
    t.amount,
    t.fee,
    bh.balance_after
FROM transactions t
JOIN transaction_categories tc ON t.category_id = tc.category_id
JOIN transaction_parties tp ON t.transaction_id = tp.transaction_id
LEFT JOIN balance_history bh ON t.transaction_id = bh.transaction_id
WHERE tp.user_id = 1
ORDER BY t.transaction_timestamp;

-- UPDATE: Update transaction status
UPDATE transactions SET status = 'completed' WHERE transaction_id = 1;

-- DELETE: Remove a tag from user (soft operation example)
DELETE FROM user_tags WHERE user_id = 1 AND tag_id = 1;

-- Re-insert for data integrity
INSERT INTO user_tags (user_id, tag_id, assigned_by) VALUES (1, 1, 'system');