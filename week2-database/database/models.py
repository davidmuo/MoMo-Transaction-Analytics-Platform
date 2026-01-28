from sqlalchemy import create_engine, Column, Integer, String, Text, Numeric, DateTime, Boolean, Enum, BigInteger, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

# enumerations used to ensure data integrity by limiting fields to valid, predefined options

class UserType(enum.Enum):
    individual = "individual"
    merchant = "merchant"
    service = "service"
    agent = "agent"

class PartyRole(enum.Enum):
    sender = "sender"
    receiver = "receiver"
    merchant = "merchant"
    agent = "agent"
    service_provider = "service_provider"

class TransactionStatus(enum.Enum):
    completed = "completed"
    pending = "pending"
    failed = "failed"
    reversed = "reversed"

class LogType(enum.Enum):
    import_ = "import"
    export = "export"
    error = "error"
    processing = "processing"
    audit = "audit"
    security = "security"

class LogLevel(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(15))
    masked_phone = Column(String(15))
    account_number = Column(String(20))
    user_type = Column(Enum(UserType), default=UserType.individual)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transaction_parties = relationship("TransactionParty", back_populates="user")
    balance_history = relationship("BalanceHistory", back_populates="user")
    user_tags = relationship("UserTag", back_populates="user")
    
    __table_args__ = (
        Index('idx_users_phone', 'phone_number'),
        Index('idx_users_name', 'full_name'),
    )
    
    def to_dict(self):
        return {
            "userId": self.user_id,
            "fullName": self.full_name,
            "phoneNumber": self.phone_number,
            "maskedPhone": self.masked_phone,
            "accountNumber": self.account_number,
            "userType": self.user_type.value if self.user_type else None,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }


class TransactionCategory(Base):
    __tablename__ = 'transaction_categories'
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(50), nullable=False, unique=True)
    category_code = Column(String(10))
    description = Column(Text)
    is_debit = Column(Boolean, default=True)
    fee_applicable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="category")
    
    def to_dict(self):
        return {
            "categoryId": self.category_id,
            "categoryName": self.category_name,
            "categoryCode": self.category_code,
            "description": self.description,
            "isDebit": self.is_debit,
            "feeApplicable": self.fee_applicable
        }


class Transaction(Base):
    __tablename__ = 'transactions'
    
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    external_txn_id = Column(String(20))
    category_id = Column(Integer, ForeignKey('transaction_categories.category_id'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    fee = Column(Numeric(10, 2), default=0)
    balance_after = Column(Numeric(15, 2))
    currency = Column(String(3), default='RWF')
    transaction_timestamp = Column(DateTime, nullable=False)
    sender_message = Column(Text)
    merchant_code = Column(String(10))
    status = Column(Enum(TransactionStatus), default=TransactionStatus.completed)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    category = relationship("TransactionCategory", back_populates="transactions")
    parties = relationship("TransactionParty", back_populates="transaction")
    raw_sms = relationship("SmsRawData", back_populates="transaction", uselist=False)
    balance_record = relationship("BalanceHistory", back_populates="transaction")
    
    __table_args__ = (
        Index('idx_txn_external_id', 'external_txn_id'),
        Index('idx_txn_timestamp', 'transaction_timestamp'),
        CheckConstraint('amount > 0', name='chk_positive_amount'),
        CheckConstraint('fee >= 0', name='chk_non_negative_fee'),
    )
    
    def to_dict(self, include_parties=False, include_category=False):
        d = {
            "transactionId": self.transaction_id,
            "externalTxnId": self.external_txn_id,
            "categoryId": self.category_id,
            "amount": float(self.amount) if self.amount else 0,
            "fee": float(self.fee) if self.fee else 0,
            "balanceAfter": float(self.balance_after) if self.balance_after else None,
            "currency": self.currency,
            "transactionTimestamp": self.transaction_timestamp.isoformat() if self.transaction_timestamp else None,
            "senderMessage": self.sender_message,
            "merchantCode": self.merchant_code,
            "status": self.status.value if self.status else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }
        if include_category and self.category:
            d["category"] = self.category.to_dict()
        if include_parties:
            d["parties"] = [p.to_dict(include_user=True) for p in self.parties]
        return d


# junction table to model the many-to-many relationship between users and transactions
class TransactionParty(Base):
    __tablename__ = 'transaction_parties'
    
    party_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    party_role = Column(Enum(PartyRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="parties")
    user = relationship("User", back_populates="transaction_parties")
    
    __table_args__ = (
        UniqueConstraint('transaction_id', 'user_id', 'party_role', name='uq_transaction_party_role'),
        Index('idx_party_transaction', 'transaction_id'),
        Index('idx_party_user', 'user_id'),
    )
    
    def to_dict(self, include_user=False):
        d = {
            "partyId": self.party_id,
            "transactionId": self.transaction_id,
            "userId": self.user_id,
            "partyRole": self.party_role.value if self.party_role else None
        }
        if include_user and self.user:
            d["user"] = self.user.to_dict()
        return d


class SystemLog(Base):
    __tablename__ = 'system_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(Enum(LogType), nullable=False)
    log_level = Column(Enum(LogLevel), default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    affected_table = Column(String(50))
    affected_records = Column(Integer, default=0)
    execution_time_ms = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50))
    
    __table_args__ = (
        Index('idx_log_type', 'log_type'),
        Index('idx_log_timestamp', 'created_at'),
    )
    
    def to_dict(self):
        return {
            "logId": self.log_id,
            "logType": self.log_type.value if self.log_type else None,
            "logLevel": self.log_level.value if self.log_level else None,
            "message": self.message,
            "affectedTable": self.affected_table,
            "affectedRecords": self.affected_records,
            "executionTimeMs": self.execution_time_ms,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "createdBy": self.created_by
        }


class SmsRawData(Base):
    __tablename__ = 'sms_raw_data'
    
    sms_id = Column(Integer, primary_key=True, autoincrement=True)
    protocol = Column(String(10))
    address = Column(String(50), nullable=False)
    sms_date_ms = Column(BigInteger)
    sms_type = Column(Integer)
    body = Column(Text, nullable=False)
    service_center = Column(String(20))
    date_sent_ms = Column(BigInteger)
    readable_date = Column(String(50))
    contact_name = Column(String(100))
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id', ondelete='SET NULL'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="raw_sms", foreign_keys=[transaction_id])
    
    __table_args__ = (
        Index('idx_sms_processed', 'is_processed'),
        Index('idx_sms_date', 'sms_date_ms'),
    )
    
    def to_dict(self):
        return {
            "smsId": self.sms_id,
            "protocol": self.protocol,
            "address": self.address,
            "smsDateMs": self.sms_date_ms,
            "body": self.body,
            "readableDate": self.readable_date,
            "isProcessed": self.is_processed,
            "processingError": self.processing_error,
            "transactionId": self.transaction_id
        }


class BalanceHistory(Base):
    __tablename__ = 'balance_history'
    
    balance_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id', ondelete='SET NULL'))
    balance_before = Column(Numeric(15, 2))
    balance_after = Column(Numeric(15, 2), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="balance_history")
    transaction = relationship("Transaction", back_populates="balance_record")
    
    def to_dict(self):
        return {
            "balanceId": self.balance_id,
            "userId": self.user_id,
            "transactionId": self.transaction_id,
            "balanceBefore": float(self.balance_before) if self.balance_before else None,
            "balanceAfter": float(self.balance_after) if self.balance_after else None,
            "recordedAt": self.recorded_at.isoformat() if self.recorded_at else None
        }


class Tag(Base):
    __tablename__ = 'tags'
    
    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(String(50), nullable=False, unique=True)
    tag_description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user_tags = relationship("UserTag", back_populates="tag")
    
    def to_dict(self):
        return {
            "tagId": self.tag_id,
            "tagName": self.tag_name,
            "tagDescription": self.tag_description
        }


class UserTag(Base):
    __tablename__ = 'user_tags'
    
    user_tag_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.tag_id', ondelete='CASCADE'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String(50))
    
    user = relationship("User", back_populates="user_tags")
    tag = relationship("Tag", back_populates="user_tags")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'tag_id', name='uq_user_tag'),
    )


# Utility functions used to set up and manage the database

def init_db(db_url="sqlite:///momo_sms.db"):
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

def seed_categories(session):
    # these are all the transaction types we found in the SMS data
    cats = [
        TransactionCategory(category_name="Incoming Transfer", category_code=None, description="Money received from another MoMo user", is_debit=False, fee_applicable=False),
        TransactionCategory(category_name="Outgoing Transfer", category_code="*165*", description="Money sent to another MoMo user", is_debit=True, fee_applicable=True),
        TransactionCategory(category_name="Merchant Payment", category_code=None, description="Payment to registered merchant", is_debit=True, fee_applicable=False),
        TransactionCategory(category_name="Bank Deposit", category_code="*113*", description="Cash deposited via bank/agent", is_debit=False, fee_applicable=False),
        TransactionCategory(category_name="Airtime Purchase", category_code="*162*", description="Mobile airtime top-up", is_debit=True, fee_applicable=False),
        TransactionCategory(category_name="Bundle Purchase", category_code="*162*", description="Data/voice bundle purchase", is_debit=True, fee_applicable=False),
        TransactionCategory(category_name="Data Bundle", category_code="*164*", description="Internet data subscription", is_debit=True, fee_applicable=False),
        TransactionCategory(category_name="Cash Withdrawal", category_code="*165*", description="Cash withdrawn from agent", is_debit=True, fee_applicable=True),
    ]
    
    for c in cats:
        exists = session.query(TransactionCategory).filter_by(category_name=c.category_name).first()
        if not exists:
            session.add(c)
    
    session.commit()
    return session.query(TransactionCategory).all()
