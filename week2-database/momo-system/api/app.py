from flask import Flask, jsonify, request
from sqlalchemy import func, desc
from datetime import datetime
from decimal import Decimal
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    init_db, get_session, User, Transaction, TransactionCategory,
    TransactionParty, SystemLog, SmsRawData, BalanceHistory,
    PartyRole, TransactionStatus, LogType, LogLevel, UserType
)

app = Flask(__name__)

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'momo_sms.db')
engine = init_db(f"sqlite:///{db_path}")


def get_db():
    return get_session(engine)


def make_response(data, code=200, msg="Success"):
    return jsonify({
        "status": "success" if code < 400 else "error",
        "code": code,
        "message": msg,
        "data": data,
        "meta": {"timestamp": datetime.utcnow().isoformat() + "Z"}
    }), code


# ============ TRANSACTIONS ============

@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    db = get_db()
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    cat_id = request.args.get('category', type=int)
    min_amt = request.args.get('min_amount', type=float)
    max_amt = request.args.get('max_amount', type=float)
    
    q = db.query(Transaction)
    
    if cat_id:
        q = q.filter(Transaction.category_id == cat_id)
    if min_amt:
        q = q.filter(Transaction.amount >= min_amt)
    if max_amt:
        q = q.filter(Transaction.amount <= max_amt)
    
    total = q.count()
    txns = q.order_by(desc(Transaction.transaction_timestamp)).offset((page-1)*limit).limit(limit).all()
    
    db.close()
    
    return make_response({
        "pagination": {
            "currentPage": page,
            "totalPages": (total + limit - 1) // limit,
            "totalRecords": total,
            "limit": limit
        },
        "transactions": [t.to_dict(include_category=True) for t in txns]
    })


@app.route('/api/transactions/<int:id>', methods=['GET'])
def get_transaction(id):
    db = get_db()
    
    txn = db.query(Transaction).filter_by(transaction_id=id).first()
    if not txn:
        db.close()
        return make_response(None, 404, "not found")
    
    result = txn.to_dict(include_parties=True, include_category=True)
    
    # include the raw sms if available
    if txn.raw_sms:
        result["rawSms"] = txn.raw_sms.to_dict()
    
    db.close()
    return make_response(result)


@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    db = get_db()
    data = request.get_json()
    
    # check required fields
    for f in ['category_id', 'amount', 'transaction_timestamp']:
        if f not in data:
            db.close()
            return make_response(None, 400, f"missing {f}")
    
    try:
        txn = Transaction(
            external_txn_id=data.get('external_txn_id'),
            category_id=data['category_id'],
            amount=Decimal(str(data['amount'])),
            fee=Decimal(str(data.get('fee', 0))),
            balance_after=Decimal(str(data['balance_after'])) if data.get('balance_after') else None,
            transaction_timestamp=datetime.fromisoformat(data['transaction_timestamp']),
            sender_message=data.get('sender_message'),
            merchant_code=data.get('merchant_code'),
            status=TransactionStatus[data.get('status', 'completed')]
        )
        db.add(txn)
        db.commit()
        
        result = txn.to_dict()
        db.close()
        return make_response(result, 201, "created")
    except Exception as e:
        db.rollback()
        db.close()
        return make_response(None, 400, str(e))


@app.route('/api/transactions/<int:id>', methods=['PUT'])
def update_transaction(id):
    db = get_db()
    
    txn = db.query(Transaction).filter_by(transaction_id=id).first()
    if not txn:
        db.close()
        return make_response(None, 404, "not found")
    
    data = request.get_json()
    
    if 'status' in data:
        txn.status = TransactionStatus[data['status']]
    if 'sender_message' in data:
        txn.sender_message = data['sender_message']
    
    db.commit()
    result = txn.to_dict()
    db.close()
    
    return make_response(result, msg="updated")


@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    db = get_db()
    
    txn = db.query(Transaction).filter_by(transaction_id=id).first()
    if not txn:
        db.close()
        return make_response(None, 404, "not found")
    
    db.delete(txn)
    db.commit()
    db.close()
    
    return make_response({"deleted": id}, msg="deleted")


# ============ USERS ============

@app.route('/api/users', methods=['GET'])
def list_users():
    db = get_db()
    
    utype = request.args.get('type')
    q = db.query(User)
    
    if utype:
        q = q.filter(User.user_type == UserType[utype])
    
    users = q.all()
    db.close()
    
    return make_response([u.to_dict() for u in users])


@app.route('/api/users/<int:id>', methods=['GET'])
def get_user(id):
    db = get_db()
    
    user = db.query(User).filter_by(user_id=id).first()
    if not user:
        db.close()
        return make_response(None, 404, "not found")
    
    result = user.to_dict()
    
    # get their transactions
    parties = db.query(TransactionParty).filter_by(user_id=id).all()
    txn_ids = [p.transaction_id for p in parties]
    
    if txn_ids:
        txns = db.query(Transaction).filter(Transaction.transaction_id.in_(txn_ids)).order_by(desc(Transaction.transaction_timestamp)).limit(10).all()
        
        result["recentTransactions"] = []
        for t in txns:
            party = next((p for p in parties if p.transaction_id == t.transaction_id), None)
            td = t.to_dict(include_category=True)
            td["partyRole"] = party.party_role.value if party else None
            result["recentTransactions"].append(td)
        
        # stats
        stats = db.query(
            func.count(Transaction.transaction_id).label('total'),
            func.sum(Transaction.amount).label('vol'),
            func.sum(Transaction.fee).label('fees')
        ).filter(Transaction.transaction_id.in_(txn_ids)).first()
        
        result["statistics"] = {
            "totalTransactions": stats.total or 0,
            "totalVolume": float(stats.vol) if stats.vol else 0,
            "totalFees": float(stats.fees) if stats.fees else 0
        }
    
    db.close()
    return make_response(result)


@app.route('/api/users/<int:id>/transactions', methods=['GET'])
def get_user_transactions(id):
    db = get_db()
    
    user = db.query(User).filter_by(user_id=id).first()
    if not user:
        db.close()
        return make_response(None, 404, "not found")
    
    parties = db.query(TransactionParty).filter_by(user_id=id).all()
    txn_ids = [p.transaction_id for p in parties]
    
    txns = db.query(Transaction).filter(Transaction.transaction_id.in_(txn_ids)).order_by(desc(Transaction.transaction_timestamp)).all()
    
    result = []
    for t in txns:
        party = next((p for p in parties if p.transaction_id == t.transaction_id), None)
        td = t.to_dict(include_category=True)
        td["partyRole"] = party.party_role.value if party else None
        result.append(td)
    
    db.close()
    return make_response(result)


@app.route('/api/users', methods=['POST'])
def create_user():
    db = get_db()
    data = request.get_json()
    
    if 'full_name' not in data:
        db.close()
        return make_response(None, 400, "need full_name")
    
    user = User(
        full_name=data['full_name'],
        phone_number=data.get('phone_number'),
        masked_phone=data.get('masked_phone'),
        account_number=data.get('account_number'),
        user_type=UserType[data.get('user_type', 'individual')]
    )
    db.add(user)
    db.commit()
    
    result = user.to_dict()
    db.close()
    return make_response(result, 201, "created")


@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    db = get_db()
    
    user = db.query(User).filter_by(user_id=id).first()
    if not user:
        db.close()
        return make_response(None, 404, "not found")
    
    db.delete(user)
    db.commit()
    db.close()
    
    return make_response({"deleted": id}, msg="deleted")


# ============ CATEGORIES ============

@app.route('/api/categories', methods=['GET'])
def list_categories():
    db = get_db()
    cats = db.query(TransactionCategory).all()
    db.close()
    return make_response([c.to_dict() for c in cats])


@app.route('/api/categories/<int:id>', methods=['GET'])
def get_category(id):
    db = get_db()
    
    cat = db.query(TransactionCategory).filter_by(category_id=id).first()
    if not cat:
        db.close()
        return make_response(None, 404, "not found")
    
    result = cat.to_dict()
    
    stats = db.query(
        func.count(Transaction.transaction_id).label('cnt'),
        func.sum(Transaction.amount).label('total'),
        func.avg(Transaction.amount).label('avg')
    ).filter(Transaction.category_id == id).first()
    
    result["statistics"] = {
        "transactionCount": stats.cnt or 0,
        "totalAmount": float(stats.total) if stats.total else 0,
        "avgAmount": float(stats.avg) if stats.avg else 0
    }
    
    db.close()
    return make_response(result)


# ============ STATS ============

@app.route('/api/stats/summary', methods=['GET'])
def summary_stats():
    db = get_db()
    
    txn_stats = db.query(
        func.count(Transaction.transaction_id).label('total'),
        func.sum(Transaction.amount).label('vol'),
        func.sum(Transaction.fee).label('fees'),
        func.avg(Transaction.amount).label('avg')
    ).first()
    
    user_cnt = db.query(func.count(User.user_id)).scalar()
    sms_cnt = db.query(func.count(SmsRawData.sms_id)).scalar()
    processed = db.query(func.count(SmsRawData.sms_id)).filter(SmsRawData.is_processed == True).scalar()
    
    db.close()
    
    return make_response({
        "transactions": {
            "total": txn_stats.total or 0,
            "totalVolume": float(txn_stats.vol) if txn_stats.vol else 0,
            "totalFees": float(txn_stats.fees) if txn_stats.fees else 0,
            "avgAmount": float(txn_stats.avg) if txn_stats.avg else 0
        },
        "users": {"total": user_cnt},
        "smsProcessing": {
            "total": sms_cnt,
            "processed": processed,
            "failed": sms_cnt - processed if sms_cnt else 0,
            "successRate": round((processed / sms_cnt * 100), 2) if sms_cnt else 0
        }
    })


@app.route('/api/stats/daily', methods=['GET'])
def daily_stats():
    db = get_db()
    
    date_str = request.args.get('date')
    if date_str:
        target = datetime.fromisoformat(date_str).date()
    else:
        target = datetime.utcnow().date()
    
    rows = db.query(
        TransactionCategory.category_name,
        func.count(Transaction.transaction_id).label('cnt'),
        func.sum(Transaction.amount).label('total'),
        func.sum(Transaction.fee).label('fees')
    ).join(TransactionCategory).filter(
        func.date(Transaction.transaction_timestamp) == target
    ).group_by(TransactionCategory.category_name).all()
    
    db.close()
    
    by_cat = []
    total_txn, total_vol, total_fees = 0, 0, 0
    
    for r in rows:
        by_cat.append({
            "categoryName": r.category_name,
            "transactionCount": r.cnt,
            "totalAmount": float(r.total) if r.total else 0,
            "totalFees": float(r.fees) if r.fees else 0
        })
        total_txn += r.cnt
        total_vol += float(r.total) if r.total else 0
        total_fees += float(r.fees) if r.fees else 0
    
    return make_response({
        "reportDate": str(target),
        "summary": {
            "totalTransactions": total_txn,
            "totalVolume": total_vol,
            "totalFees": total_fees
        },
        "byCategory": by_cat
    })


@app.route('/api/stats/category-breakdown', methods=['GET'])
def category_breakdown():
    db = get_db()
    
    rows = db.query(
        TransactionCategory.category_name,
        TransactionCategory.is_debit,
        func.count(Transaction.transaction_id).label('cnt'),
        func.sum(Transaction.amount).label('total'),
        func.avg(Transaction.amount).label('avg')
    ).join(TransactionCategory).group_by(
        TransactionCategory.category_name, TransactionCategory.is_debit
    ).order_by(desc('total')).all()
    
    db.close()
    
    result = []
    for r in rows:
        result.append({
            "categoryName": r.category_name,
            "isDebit": r.is_debit,
            "transactionCount": r.cnt,
            "totalAmount": float(r.total) if r.total else 0,
            "avgAmount": float(r.avg) if r.avg else 0
        })
    
    return make_response(result)


# ============ LOGS & SMS ============

@app.route('/api/logs', methods=['GET'])
def get_logs():
    db = get_db()
    
    ltype = request.args.get('type')
    limit = request.args.get('limit', 50, type=int)
    
    q = db.query(SystemLog)
    if ltype:
        q = q.filter(SystemLog.log_type == LogType[ltype])
    
    logs = q.order_by(desc(SystemLog.created_at)).limit(limit).all()
    db.close()
    
    return make_response([l.to_dict() for l in logs])


@app.route('/api/sms', methods=['GET'])
def get_sms():
    db = get_db()
    
    proc = request.args.get('processed')
    limit = request.args.get('limit', 50, type=int)
    
    q = db.query(SmsRawData)
    if proc is not None:
        q = q.filter(SmsRawData.is_processed == (proc.lower() == 'true'))
    
    sms_list = q.order_by(desc(SmsRawData.sms_date_ms)).limit(limit).all()
    db.close()
    
    return make_response([s.to_dict() for s in sms_list])


@app.route('/api/health', methods=['GET'])
def health():
    return make_response({"status": "ok", "db": "connected"})


@app.route('/', methods=['GET'])
def index():
    # just list available endpoints
    return jsonify({
        "name": "MoMo SMS API",
        "version": "1.0",
        "endpoints": {
            "transactions": ["GET /api/transactions", "GET /api/transactions/<id>", "POST", "PUT", "DELETE"],
            "users": ["GET /api/users", "GET /api/users/<id>", "GET /api/users/<id>/transactions", "POST", "DELETE"],
            "categories": ["GET /api/categories", "GET /api/categories/<id>"],
            "stats": ["GET /api/stats/summary", "GET /api/stats/daily", "GET /api/stats/category-breakdown"],
            "system": ["GET /api/logs", "GET /api/sms", "GET /api/health"]
        }
    })


if __name__ == '__main__':
    print("Starting server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)