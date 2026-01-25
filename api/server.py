import http.server
import socketserver
import json
import xml.etree.ElementTree as ET
import base64

# Load your transactions from XML
tree = ET.parse("modified_sms_v2.xml")
root = tree.getroot()

transactions = []
for i, sms in enumerate(root, start=1):
    transaction = sms.attrib
    transaction["id"] = str(i)
    transactions.append(transaction)

# --- Helper function for authentication ---
def check_auth(headers):
    auth_header = headers.get("Authorization")
    if auth_header is None:
        return False
    try:
        auth_type, encoded = auth_header.split(" ")
        if auth_type != "Basic":
            return False
        decoded = base64.b64decode(encoded).decode()
        username, password = decoded.split(":")
        return username == "admin" and password == "password123"
    except:
        return False

class MyHandler(http.server.SimpleHTTPRequestHandler):

    # --- GET ---
    def do_GET(self):
        if not check_auth(self.headers):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="API"')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path == "/transactions":
            response = json.dumps(transactions).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response)

        elif self.path.startswith("/transactions/"):
            trans_id = self.path.split("/")[-1]
            found = None
            for t in transactions:
                if t.get("id") == trans_id:
                    found = t
                    break

            if found:
                response = json.dumps(found).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Transaction not found")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    # --- POST ---
    def do_POST(self):
        if not check_auth(self.headers):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="API"')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path == "/transactions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            new_id = str(len(transactions) + 1)
            data["id"] = new_id
            transactions.append(data)

            response = json.dumps(data).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.end_headers()

    # --- PUT ---
    def do_PUT(self):
        if not check_auth(self.headers):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="API"')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path.startswith("/transactions/"):
            trans_id = self.path.split("/")[-1]
            found = None
            for t in transactions:
                if t.get("id") == trans_id:
                    found = t
                    break

            if found:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)

                for key, value in data.items():
                    if key != "id":
                        found[key] = value

                response = json.dumps(found).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Transaction not found")
        else:
            self.send_response(404)
            self.end_headers()

    # --- DELETE ---
    def do_DELETE(self):
        if not check_auth(self.headers):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="API"')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path.startswith("/transactions/"):
            trans_id = self.path.split("/")[-1]
            found = None
            for i, t in enumerate(transactions):
                if t.get("id") == trans_id:
                    found = i
                    break

            if found is not None:
                deleted = transactions.pop(found)
                response = json.dumps({
                    "message": "Transaction deleted",
                    "transaction": deleted
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Transaction not found")
        else:
            self.send_response(404)
            self.end_headers()


# Start the server
PORT = 8000
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
