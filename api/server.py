import http.server
import socketserver
import json
import xml.etree.ElementTree as ET
import uuid
from datetime import datetime

# --- Load transactions from XML ---
tree = ET.parse("modified_sms_v2.xml")
root = tree.getroot()

transactions = []
transactions_dict = {}  # dictionary for O(1) lookup by id

for sms in root:
    transaction = sms.attrib
    # Use UUIDs for unique ID
    transaction_id = str(uuid.uuid4())
    transaction["id"] = transaction_id
    # Add timestamps
    transaction["createdAt"] = datetime.now().isoformat()
    transaction["updatedAt"] = None
    transactions.append(transaction)
    transactions_dict[transaction_id] = transaction

# --- HTTP Handler ---
class MyHandler(http.server.SimpleHTTPRequestHandler):

    # --- Helper methods ---
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _get_auth(self):
        """Get credentials from Basic Auth"""
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            import base64
            encoded = auth_header.split(" ")[1]
            decoded = base64.b64decode(encoded).decode()
            username, password = decoded.split(":")
            return username, password
        return None, None

    def _check_auth(self):
        username, password = self._get_auth()
        # hardcoded for assignment
        if username == "admin" and password == "password123":
            return True
        return False

    # --- GET ---
    def do_GET(self):
        if not self._check_auth():
            return self._send_json({"error": "Unauthorized"}, 401)

        if self.path == "/transactions":
            return self._send_json({"count": len(transactions), "transactions": transactions})

        elif self.path.startswith("/transactions/"):
            trans_id = self.path.split("/")[-1]
            transaction = transactions_dict.get(trans_id)
            if transaction:
                return self._send_json(transaction)
            else:
                return self._send_json({"error": "Transaction not found"}, 404)
        else:
            return self._send_json({"error": "Not Found"}, 404)

    # --- POST ---
    def do_POST(self):
        if not self._check_auth():
            return self._send_json({"error": "Unauthorized"}, 401)

        if self.path != "/transactions":
            return self._send_json({"error": "Not Found"}, 404)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        # assign UUID if not provided
        new_id = str(uuid.uuid4())
        data["id"] = new_id
        data["createdAt"] = datetime.now().isoformat()
        data["updatedAt"] = None

        transactions.append(data)
        transactions_dict[new_id] = data

        return self._send_json(data, 201)

    # --- PUT ---
    def do_PUT(self):
        if not self._check_auth():
            return self._send_json({"error": "Unauthorized"}, 401)

        if not self.path.startswith("/transactions/"):
            return self._send_json({"error": "Not Found"}, 404)

        trans_id = self.path.split("/")[-1]
        transaction = transactions_dict.get(trans_id)
        if not transaction:
            return self._send_json({"error": "Transaction not found"}, 404)

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        # update fields (except ID)
        for k, v in data.items():
            if k != "id":
                transaction[k] = v
        transaction["updatedAt"] = datetime.now().isoformat()

        return self._send_json(transaction, 200)

    # --- DELETE ---
    def do_DELETE(self):
        if not self._check_auth():
            return self._send_json({"error": "Unauthorized"}, 401)

        if not self.path.startswith("/transactions/"):
            return self._send_json({"error": "Not Found"}, 404)

        trans_id = self.path.split("/")[-1]
        transaction = transactions_dict.pop(trans_id, None)
        if transaction:
            # remove from list as well
            transactions[:] = [t for t in transactions if t["id"] != trans_id]
            return self._send_json({"message": "Transaction deleted", "transaction": transaction})
        else:
            return self._send_json({"error": "Transaction not found"}, 404)


# --- Run the server ---
PORT = 8000
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
