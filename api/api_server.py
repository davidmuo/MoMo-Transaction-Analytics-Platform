from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import base64
from urllib.parse import urlparse, parse_qs

# Simple in-memory storage
transactions = []
next_id = 1

# Authentication credentials (username:password)
VALID_CREDENTIALS = {
    'admin': 'password123',
    'user': 'securepass'
}

class APIHandler(BaseHTTPRequestHandler):
    
    def authenticate(self):
        """
        Check Basic Authentication
        Returns True if authenticated, False otherwise
        """
        auth_header = self.headers.get('Authorization')
        
        if not auth_header:
            return False
        
        try:
            # Parse "Basic base64string"
            auth_type, auth_string = auth_header.split(' ')
            
            if auth_type.lower() != 'basic':
                return False
            
            # Decode base64
            decoded = base64.b64decode(auth_string).decode('utf-8')
            username, password = decoded.split(':')
            
            # Validate credentials
            return VALID_CREDENTIALS.get(username) == password
        
        except Exception:
            return False
    
    def send_unauthorized(self):
        """
        Send 401 Unauthorized response
        """
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Transaction API"')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'error': 'Unauthorized', 'message': 'Valid credentials required'}
        self.wfile.write(json.dumps(response).encode())
    
    def send_json_response(self, data, status=200):
        """
        Send JSON response
        """
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        """
        Handle GET requests
        """
        if not self.authenticate():
            self.send_unauthorized()
            return
        
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')
        
        # GET /transactions - List all transactions
        if path_parts[0] == 'transactions' and len(path_parts) == 1:
            self.send_json_response({'transactions': transactions, 'count': len(transactions)})
        
        # GET /transactions/{id} - Get single transaction
        elif path_parts[0] == 'transactions' and len(path_parts) == 2:
            try:
                tid = int(path_parts[1])
                transaction = next((t for t in transactions if t['id'] == tid), None)
                
                if transaction:
                    self.send_json_response(transaction)
                else:
                    self.send_json_response({'error': 'Not found', 'message': f'Transaction {tid} not found'}, 404)
            
            except ValueError:
                self.send_json_response({'error': 'Invalid ID', 'message': 'Transaction ID must be an integer'}, 400)
        
        else:
            self.send_json_response({'error': 'Not found', 'message': 'Endpoint not found'}, 404)
    
    def do_POST(self):
        """
        Handle POST requests - Create new transaction
        """
        if not self.authenticate():
            self.send_unauthorized()
            return
        
        global next_id
        
        if self.path == '/transactions':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                new_transaction = json.loads(post_data)
                
                # Assign ID
                new_transaction['id'] = next_id
                next_id += 1
                
                transactions.append(new_transaction)
                
                self.send_json_response({'message': 'Transaction created', 'transaction': new_transaction}, 201)
            
            except json.JSONDecodeError:
                self.send_json_response({'error': 'Invalid JSON', 'message': 'Request body must be valid JSON'}, 400)
            except Exception as e:
                self.send_json_response({'error': 'Server error', 'message': str(e)}, 500)
        
        else:
            self.send_json_response({'error': 'Not found', 'message': 'Endpoint not found'}, 404)
    
    def do_PUT(self):
        """
        Handle PUT requests - Update existing transaction
        """
        if not self.authenticate():
            self.send_unauthorized()
            return
        
        path_parts = self.path.strip('/').split('/')
        
        if path_parts[0] == 'transactions' and len(path_parts) == 2:
            try:
                tid = int(path_parts[1])
                
                # Find transaction
                transaction = next((t for t in transactions if t['id'] == tid), None)
                
                if not transaction:
                    self.send_json_response({'error': 'Not found', 'message': f'Transaction {tid} not found'}, 404)
                    return
                
                # Update transaction
                content_length = int(self.headers['Content-Length'])
                put_data = self.rfile.read(content_length)
                update_data = json.loads(put_data)
                
                # Preserve ID
                update_data['id'] = tid
                
                # Update in list
                idx = transactions.index(transaction)
                transactions[idx] = update_data
                
                self.send_json_response({'message': 'Transaction updated', 'transaction': update_data})
            
            except ValueError:
                self.send_json_response({'error': 'Invalid ID', 'message': 'Transaction ID must be an integer'}, 400)
            except json.JSONDecodeError:
                self.send_json_response({'error': 'Invalid JSON', 'message': 'Request body must be valid JSON'}, 400)
            except Exception as e:
                self.send_json_response({'error': 'Server error', 'message': str(e)}, 500)
        
        else:
            self.send_json_response({'error': 'Not found', 'message': 'Endpoint not found'}, 404)
    
    def do_DELETE(self):
        """
        Handle DELETE requests - Delete transaction
        """
        if not self.authenticate():
            self.send_unauthorized()
            return
        
        path_parts = self.path.strip('/').split('/')
        
        if path_parts[0] == 'transactions' and len(path_parts) == 2:
            try:
                tid = int(path_parts[1])
                
                # Find and remove transaction
                transaction = next((t for t in transactions if t['id'] == tid), None)
                
                if transaction:
                    transactions.remove(transaction)
                    self.send_json_response({'message': 'Transaction deleted', 'id': tid})
                else:
                    self.send_json_response({'error': 'Not found', 'message': f'Transaction {tid} not found'}, 404)
            
            except ValueError:
                self.send_json_response({'error': 'Invalid ID', 'message': 'Transaction ID must be an integer'}, 400)
        
        else:
            self.send_json_response({'error': 'Not found', 'message': 'Endpoint not found'}, 404)

def load_initial_data():
    """
    Load transactions from JSON file
    """
    global transactions, next_id
    try:
        with open('transactions.json', 'r') as f:
            transactions = json.load(f)
            if transactions:
                next_id = max(t['id'] for t in transactions) + 1
            print(f"Loaded {len(transactions)} transactions")
    except FileNotFoundError:
        print("No transactions.json found. Starting with empty data.")
        transactions = []

def run_server(port=8000):
    """
    Start the API server
    """
    load_initial_data()
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIHandler)
    
    print(f"\n{'='*60}")
    print(f"MoMo SMS Transaction API Server")
    print(f"{'='*60}")
    print(f"Server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET    /transactions       - List all transactions")
    print(f"  GET    /transactions/{{id}} - Get single transaction")
    print(f"  POST   /transactions       - Create new transaction")
    print(f"  PUT    /transactions/{{id}} - Update transaction")
    print(f"  DELETE /transactions/{{id}} - Delete transaction")
    print(f"\nAuthentication: Basic Auth")
    print(f"  Username: admin | Password: password123")
    print(f"  Username: user  | Password: securepass")
    print(f"{'='*60}\n")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()