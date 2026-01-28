CREATE DATABASE IF NOT EXISTS momo_sms_db;
USE momo_sms_db;

DROP TABLE IF EXISTS System_Logs;
DROP TABLE IF EXISTS Transaction_Merchant;
DROP TABLE IF EXISTS Merchants;
DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Transaction_Categories;
DROP TABLE IF EXISTS Users;

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(15) UNIQUE NOT NULL COMMENT 'User phone number in international format',
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    account_status ENUM('active', 'suspended', 'closed') DEFAULT 'active',

    CONSTRAINT chk_phone_format CHECK (phone_number REGEXP '^250[0-9]{9}$')
);

    CREATE INDEX idx_users_phone ON users(phone_number);
    CREATE INDEX idx_users_status ON users(account_status);
    CREATE INDEX idx_users_email ON users(email);


CREATE TABLE Transaction_Categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

) ENGINE=InnoDB ;

CREATE TABLE Merchants (
    merchant_id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    merchant_code VARCHAR(20) UNIQUE NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_code (merchant_code),
    INDEX idx_phone (phone_number)
) ENGINE=InnoDB;

CREATE TABLE Transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT,
    category_id INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RWF',
    transaction_fee DECIMAL(10,2) DEFAULT 0.00,
    transaction_date DATETIME NOT NULL,
    description TEXT,

    -- Foreign key constraints
    CONSTRAINT fk_sender
        FOREIGN KEY (sender_id)
        REFERENCES Users(user_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_receiver
        FOREIGN KEY (receiver_id)
        REFERENCES Users(user_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_category
        FOREIGN KEY (category_id)
        REFERENCES Transaction_Categories(category_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    -- Indexes for performance
    INDEX idx_sender (sender_id),
    INDEX idx_receiver (receiver_id),
    INDEX idx_category (category_id),
    INDEX idx_date (transaction_date),
    INDEX idx_amount (amount)
) ENGINE=InnoDB;

CREATE TABLE Transaction_Merchant (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    merchant_id INT NOT NULL,
    merchant_fee DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_tm_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES Transactions(transaction_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_tm_merchant
        FOREIGN KEY (merchant_id)
        REFERENCES Merchants(merchant_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- to avoid duplicates
    CONSTRAINT uq_transaction_merchant UNIQUE (transaction_id, merchant_id),

    -- Indexes
    INDEX idx_transaction (transaction_id),
    INDEX idx_merchant (merchant_id)
) ENGINE=InnoDB;

CREATE TABLE System_Logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    log_type ENUM('info', 'warning', 'error', 'debug') NOT NULL,
    message TEXT NOT NULL,
    transaction_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_data JSON COMMENT 'Extra context data in JSON format',

    --Foreign key constraint
    CONSTRAINT fk_log_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES Transactions(transaction_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    -- Indexes
    INDEX idx_type (log_type),
    INDEX idx_timestamp (timestamp),
    INDEX idx_transaction (transaction_id)
) ENGINE=InnoDB;