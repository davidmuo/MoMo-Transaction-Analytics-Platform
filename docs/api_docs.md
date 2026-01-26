# MoMo SMS Transaction API Documentation

## Overview
This REST API provides access to SMS transaction records from a mobile money service. All endpoints require Basic Authentication.

**Base URL:** `http://localhost:8000`

**Authentication:** Basic Authentication (username:password encoded in base64)

Valid credentials:
- Username: `admin` | Password: `password123`
- Username: `user` | Password: `securepass`

---

## Endpoints

### 1. List All Transactions

**Endpoint:** `GET /transactions`

**Description:** Retrieves all SMS transactions

**Authentication:** Required

**Request Example:**
```bash
curl -u admin:password123 http://localhost:8000/transactions
```

**Response Example (200 OK):**
```json
{
  "transactions": [
    {
      "id": 1,
      "type": "DEPOSIT",
      "amount": "5000",
      "sender": "USER123",
      "receiver": "MERCHANT456",
      "timestamp": "2024-01-15T10:30:00",
      "body": "You have deposited 5000 RWF",
      "address": "+250788123456"
    },
    {
      "id": 2,
      "type": "WITHDRAWAL",
      "amount": "2000",
      "sender": "USER789",
      "receiver": "ATM001",
      "timestamp": "2024-01-15T11:45:00",
      "body": "You have withdrawn 2000 RWF",
      "address": "+250788654321"
    }
  ],
  "count": 2
}
```

**Error Codes:**
- `401 Unauthorized` - Invalid or missing credentials

---

### 2. Get Single Transaction

**Endpoint:** `GET /transactions/{id}`

**Description:** Retrieves a specific transaction by ID

**Authentication:** Required

**URL Parameters:**
- `id` (integer) - Transaction ID

**Request Example:**
```bash
curl -u admin:password123 http://localhost:8000/transactions/1
```

**Response Example (200 OK):**
```json
{
  "id": 1,
  "type": "DEPOSIT",
  "amount": "5000",
  "sender": "USER123",
  "receiver": "MERCHANT456",
  "timestamp": "2024-01-15T10:30:00",
  "body": "You have deposited 5000 RWF",
  "address": "+250788123456"
}
```

**Error Codes:**
- `400 Bad Request` - Invalid transaction ID format
- `401 Unauthorized` - Invalid or missing credentials
- `404 Not Found` - Transaction not found

---

### 3. Create New Transaction

**Endpoint:** `POST /transactions`

**Description:** Creates a new SMS transaction

**Authentication:** Required

**Request Body:** JSON object with transaction details

**Request Example:**
```bash
curl -u admin:password123 -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "TRANSFER",
    "amount": "10000",
    "sender": "USER999",
    "receiver": "USER888",
    "timestamp": "2024-01-16T09:00:00",
    "body": "You have transferred 10000 RWF",
    "address": "+250788999888"
  }'
```

**Response Example (201 Created):**
```json
{
  "message": "Transaction created",
  "transaction": {
    "id": 3,
    "type": "TRANSFER",
    "amount": "10000",
    "sender": "USER999",
    "receiver": "USER888",
    "timestamp": "2024-01-16T09:00:00",
    "body": "You have transferred 10000 RWF",
    "address": "+250788999888"
  }
}
```

**Error Codes:**
- `400 Bad Request` - Invalid JSON format
- `401 Unauthorized` - Invalid or missing credentials
- `500 Internal Server Error` - Server processing error

---

### 4. Update Existing Transaction

**Endpoint:** `PUT /transactions/{id}`

**Description:** Updates an existing transaction

**Authentication:** Required

**URL Parameters:**
- `id` (integer) - Transaction ID

**Request Body:** JSON object with updated transaction details

**Request Example:**
```bash
curl -u admin:password123 -X PUT http://localhost:8000/transactions/1 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "DEPOSIT",
    "amount": "7500",
    "sender": "USER123",
    "receiver": "MERCHANT456",
    "timestamp": "2024-01-15T10:30:00",
    "body": "You have deposited 7500 RWF (updated)",
    "address": "+250788123456"
  }'
```

**Response Example (200 OK):**
```json
{
  "message": "Transaction updated",
  "transaction": {
    "id": 1,
    "type": "DEPOSIT",
    "amount": "7500",
    "sender": "USER123",
    "receiver": "MERCHANT456",
    "timestamp": "2024-01-15T10:30:00",
    "body": "You have deposited 7500 RWF (updated)",
    "address": "+250788123456"
  }
}
```

**Error Codes:**
- `400 Bad Request` - Invalid ID format or JSON
- `401 Unauthorized` - Invalid or missing credentials
- `404 Not Found` - Transaction not found
- `500 Internal Server Error` - Server processing error

---

### 5. Delete Transaction

**Endpoint:** `DELETE /transactions/{id}`

**Description:** Deletes a transaction

**Authentication:** Required

**URL Parameters:**
- `id` (integer) - Transaction ID

**Request Example:**
```bash
curl -u admin:password123 -X DELETE http://localhost:8000/transactions/1
```

**Response Example (200 OK):**
```json
{
  "message": "Transaction deleted",
  "id": 1
}
```

**Error Codes:**
- `400 Bad Request` - Invalid transaction ID format
- `401 Unauthorized` - Invalid or missing credentials
- `404 Not Found` - Transaction not found

---

## Authentication

All endpoints require Basic Authentication. Include credentials in the Authorization header:

```
Authorization: Basic base64(username:password)
```

**Example with curl:**
```bash
curl -u username:password http://localhost:8000/transactions
```

**Example with explicit header:**
```bash
curl -H "Authorization: Basic YWRtaW46cGFzc3dvcmQxMjM=" http://localhost:8000/transactions
```

**Unauthorized Response (401):**
```json
{
  "error": "Unauthorized",
  "message": "Valid credentials required"
}
```

---

## Error Handling

All errors return a JSON response with the following structure:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common HTTP Status Codes:**
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Authentication failed
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Testing with Postman

1. **Set Authentication:**
   - Go to Authorization tab
   - Select "Basic Auth"
   - Enter username and password

2. **Test GET:**
   - Method: GET
   - URL: `http://localhost:8000/transactions`

3. **Test POST:**
   - Method: POST
   - URL: `http://localhost:8000/transactions`
   - Body: raw JSON

4. **Test PUT:**
   - Method: PUT
   - URL: `http://localhost:8000/transactions/1`
   - Body: raw JSON

5. **Test DELETE:**
   - Method: DELETE
   - URL: `http://localhost:8000/transactions/1`