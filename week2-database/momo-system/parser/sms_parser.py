import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    User, Transaction, TransactionCategory, TransactionParty, 
    SmsRawData, SystemLog, PartyRole, LogType, LogLevel, UserType
)

class MoMoSmsParser:
    
    PATTERNS = {
        'incoming_transfer': {
            'regex': r'You have received (\d[\d,]*) RWF from (.+?) \((\*+\d+)\).*?at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?(?:Message from sender: (.*?)\. )?Your new balance[:\s]*(\d[\d,]*) RWF.*?Financial Transaction Id: (\d+)',
            'category': 'Incoming Transfer'
        },
        'outgoing_transfer': {
            'regex': r'\*165\*S\*(\d[\d,]*) RWF transferred to (.+?) \((\d+)\) from (\d+) at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Fee was: (\d[\d,]*) RWF.*?New balance: (\d[\d,]*) RWF',
            'category': 'Outgoing Transfer'
        },
        'merchant_payment': {
            'regex': r'TxId: (\d+)\. Your payment of (\d[\d,]*) RWF to (.+?) (\d+) has been completed at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Your new balance: (\d[\d,]*) RWF.*?Fee was (\d[\d,]*) RWF',
            'category': 'Merchant Payment'
        },
        'bank_deposit': {
            'regex': r'\*113\*R\*A bank deposit of (\d[\d,]*) RWF has been added.*?at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?NEW BALANCE\s*[:\s]*(\d[\d,]*) RWF',
            'category': 'Bank Deposit'
        },
        'airtime_purchase': {
            'regex': r'\*162\*TxId:(\d+)\*S\*Your payment of (\d[\d,]*) RWF to Airtime.*?at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Fee was (\d[\d,]*) RWF.*?new balance: (\d[\d,]*) RWF',
            'category': 'Airtime Purchase'
        },
        'bundle_purchase': {
            'regex': r'\*162\*TxId:(\d+)\*S\*Your payment of (\d[\d,]*) RWF to Bundles and Packs.*?at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?Fee was (\d[\d,]*) RWF.*?new balance: (\d[\d,]*) RWF',
            'category': 'Bundle Purchase'
        },
        'data_bundle': {
            'regex': r'\*164\*S\*.*?transaction of (\d[\d,]*) RWF by Data Bundle MTN.*?at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?new balance[:\s]*(\d[\d,]*)\s*RWF.*?Fee was (\d[\d,]*) RWF.*?Financial Transaction Id: (\d+)',
            'category': 'Data Bundle'
        }
    }
    
    def __init__(self, session):
        self.session = session
        self.categories = {}
        self.users_cache = {}
        self.owner = None
        self._load_categories()
        self._setup_owner()
    
    def _load_categories(self):
        cats = self.session.query(TransactionCategory).all()
        for c in cats:
            self.categories[c.category_name] = c
    
    def _setup_owner(self):
        self.owner = self.session.query(User).filter_by(account_number='36521838').first()
        if not self.owner:
            self.owner = User(
                full_name="Account Owner",
                phone_number="250795963036",
                account_number="36521838",
                user_type=UserType.individual
            )
            self.session.add(self.owner)
            self.session.commit()
    
    def _parse_amount(self, amt):
        return Decimal(amt.replace(',', ''))
    
    def _parse_ts(self, ts):
        return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
    
    def _get_or_create_user(self, name, phone=None, masked=None, utype=UserType.individual):
        key = f"{name}_{phone}_{masked}"
        if key in self.users_cache:
            return self.users_cache[key]
        
        q = self.session.query(User).filter_by(full_name=name)
        if phone:
            q = q.filter_by(phone_number=phone)
        usr = q.first()
        
        if not usr:
            usr = User(full_name=name, phone_number=phone, masked_phone=masked, user_type=utype)
            self.session.add(usr)
            self.session.commit()
        
        self.users_cache[key] = usr
        return usr
    
    def _parse_incoming_transfer(self, body, sms):
        m = re.search(self.PATTERNS['incoming_transfer']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        amt = self._parse_amount(m.group(1))
        sender_name = m.group(2).strip()
        masked = m.group(3)
        ts = self._parse_ts(m.group(4))
        msg = m.group(5) if m.group(5) else None
        bal = self._parse_amount(m.group(6))
        txid = m.group(7)
        
        sender = self._get_or_create_user(sender_name, masked=masked)
        cat = self.categories['Incoming Transfer']
        
        txn = Transaction(
            external_txn_id=txid,
            category_id=cat.category_id,
            amount=amt,
            fee=Decimal('0'),
            balance_after=bal,
            transaction_timestamp=ts,
            sender_message=msg
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.receiver))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=sender.user_id, party_role=PartyRole.sender))
        self.session.commit()
        
        return txn
    
    def _parse_outgoing_transfer(self, body, sms):
        m = re.search(self.PATTERNS['outgoing_transfer']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        amt = self._parse_amount(m.group(1))
        recv_name = m.group(2).strip()
        recv_phone = m.group(3)
        ts = self._parse_ts(m.group(5))
        fee = self._parse_amount(m.group(6))
        bal = self._parse_amount(m.group(7))
        
        receiver = self._get_or_create_user(recv_name, phone=recv_phone)
        cat = self.categories['Outgoing Transfer']
        
        txn = Transaction(
            external_txn_id=None,
            category_id=cat.category_id,
            amount=amt,
            fee=fee,
            balance_after=bal,
            transaction_timestamp=ts
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.sender))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=receiver.user_id, party_role=PartyRole.receiver))
        self.session.commit()
        
        return txn
    
    def _parse_merchant_payment(self, body, sms):
        m = re.search(self.PATTERNS['merchant_payment']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        txid = m.group(1)
        amt = self._parse_amount(m.group(2))
        merch_name = m.group(3).strip()
        merch_code = m.group(4)
        ts = self._parse_ts(m.group(5))
        bal = self._parse_amount(m.group(6))
        fee = self._parse_amount(m.group(7))
        
        merchant = self._get_or_create_user(merch_name, utype=UserType.merchant)
        cat = self.categories['Merchant Payment']
        
        txn = Transaction(
            external_txn_id=txid,
            category_id=cat.category_id,
            amount=amt,
            fee=fee,
            balance_after=bal,
            transaction_timestamp=ts,
            merchant_code=merch_code
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.sender))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=merchant.user_id, party_role=PartyRole.merchant))
        self.session.commit()
        
        return txn
    
    def _parse_bank_deposit(self, body, sms):
        m = re.search(self.PATTERNS['bank_deposit']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        amt = self._parse_amount(m.group(1))
        ts = self._parse_ts(m.group(2))
        bal = self._parse_amount(m.group(3))
        
        cat = self.categories['Bank Deposit']
        
        txn = Transaction(
            external_txn_id=None,
            category_id=cat.category_id,
            amount=amt,
            fee=Decimal('0'),
            balance_after=bal,
            transaction_timestamp=ts
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.receiver))
        self.session.commit()
        
        return txn
    
    def _parse_airtime(self, body, sms):
        m = re.search(self.PATTERNS['airtime_purchase']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        txid = m.group(1)
        amt = self._parse_amount(m.group(2))
        ts = self._parse_ts(m.group(3))
        fee = self._parse_amount(m.group(4))
        bal = self._parse_amount(m.group(5))
        
        svc = self._get_or_create_user("MTN Airtime", utype=UserType.service)
        cat = self.categories['Airtime Purchase']
        
        txn = Transaction(
            external_txn_id=txid,
            category_id=cat.category_id,
            amount=amt,
            fee=fee,
            balance_after=bal,
            transaction_timestamp=ts
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.sender))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=svc.user_id, party_role=PartyRole.service_provider))
        self.session.commit()
        
        return txn
    
    def _parse_bundle(self, body, sms):
        m = re.search(self.PATTERNS['bundle_purchase']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        txid = m.group(1)
        amt = self._parse_amount(m.group(2))
        ts = self._parse_ts(m.group(3))
        fee = self._parse_amount(m.group(4))
        bal = self._parse_amount(m.group(5))
        
        svc = self._get_or_create_user("Bundles and Packs", utype=UserType.service)
        cat = self.categories['Bundle Purchase']
        
        txn = Transaction(
            external_txn_id=txid,
            category_id=cat.category_id,
            amount=amt,
            fee=fee,
            balance_after=bal,
            transaction_timestamp=ts
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.sender))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=svc.user_id, party_role=PartyRole.service_provider))
        self.session.commit()
        
        return txn
    
    def _parse_data_bundle(self, body, sms):
        m = re.search(self.PATTERNS['data_bundle']['regex'], body, re.DOTALL)
        if not m:
            return None
        
        amt = self._parse_amount(m.group(1))
        ts = self._parse_ts(m.group(2))
        bal = self._parse_amount(m.group(3))
        fee = self._parse_amount(m.group(4))
        txid = m.group(5)
        
        svc = self._get_or_create_user("Data Bundle MTN", utype=UserType.service)
        cat = self.categories['Data Bundle']
        
        txn = Transaction(
            external_txn_id=txid,
            category_id=cat.category_id,
            amount=amt,
            fee=fee,
            balance_after=bal,
            transaction_timestamp=ts
        )
        self.session.add(txn)
        self.session.commit()
        
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=self.owner.user_id, party_role=PartyRole.sender))
        self.session.add(TransactionParty(transaction_id=txn.transaction_id, user_id=svc.user_id, party_role=PartyRole.service_provider))
        self.session.commit()
        
        return txn
    
    def parse_sms(self, body, sms_raw):
        parsers = [
            ('incoming_transfer', self._parse_incoming_transfer),
            ('outgoing_transfer', self._parse_outgoing_transfer),
            ('merchant_payment', self._parse_merchant_payment),
            ('bank_deposit', self._parse_bank_deposit),
            ('airtime_purchase', self._parse_airtime),
            ('bundle_purchase', self._parse_bundle),
            ('data_bundle', self._parse_data_bundle),
        ]
        
        for name, fn in parsers:
            try:
                txn = fn(body, sms_raw)
                if txn:
                    return txn, name
            except:
                continue
        
        return None, None
    
    def parse_xml_file(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        stats = {'total': 0, 'parsed': 0, 'failed': 0, 'by_type': {}}
        
        t0 = datetime.utcnow()
        
        self.session.add(SystemLog(
            log_type=LogType.import_,
            log_level=LogLevel.INFO,
            message=f"Starting import from {filepath}",
            affected_table='sms_raw_data',
            created_by='parser'
        ))
        self.session.commit()
        
        for elem in root.findall('sms'):
            stats['total'] += 1
            
            addr = elem.get('address', '')
            if addr != 'M-Money':
                continue
            
            body = elem.get('body', '')
            
            raw = SmsRawData(
                protocol=elem.get('protocol'),
                address=addr,
                sms_date_ms=int(elem.get('date', 0)),
                sms_type=int(elem.get('type', 0)),
                body=body,
                service_center=elem.get('service_center'),
                date_sent_ms=int(elem.get('date_sent', 0)),
                readable_date=elem.get('readable_date'),
                contact_name=elem.get('contact_name'),
                is_processed=False
            )
            self.session.add(raw)
            self.session.commit()
            
            txn, ttype = self.parse_sms(body, raw)
            
            if txn:
                raw.is_processed = True
                raw.transaction_id = txn.transaction_id
                stats['parsed'] += 1
                stats['by_type'][ttype] = stats['by_type'].get(ttype, 0) + 1
            else:
                raw.is_processed = False
                raw.processing_error = "no matching pattern"
                stats['failed'] += 1
            
            self.session.commit()
        
        t1 = datetime.utcnow()
        ms = int((t1 - t0).total_seconds() * 1000)
        
        self.session.add(SystemLog(
            log_type=LogType.import_,
            log_level=LogLevel.INFO,
            message=f"Done: {stats['parsed']}/{stats['total']} parsed",
            affected_table='transactions',
            affected_records=stats['parsed'],
            execution_time_ms=ms,
            created_by='parser'
        ))
        self.session.commit()
        
        return stats


def main():
    from database.models import init_db, get_session, seed_categories
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'momo_sms.db')
    engine = init_db(f"sqlite:///{db_path}")
    session = get_session(engine)
    
    seed_categories(session)
    
    xml_file = "modified_sms_v2__2_.xml"
    if not os.path.exists(xml_file):
        xml_file = input("xml file path: ").strip()
    
    parser = MoMoSmsParser(session)
    stats = parser.parse_xml_file(xml_file)
    
    print("\n" + "="*50)
    print("DONE")
    print("="*50)
    print(f"Total: {stats['total']}")
    print(f"Parsed: {stats['parsed']}")
    print(f"Failed: {stats['failed']}")
    print("\nBy type:")
    for t, c in stats['by_type'].items():
        print(f"  {t}: {c}")
    
    session.close()


if __name__ == "__main__":
    main()