import xml.etree.ElementTree as ET
import json

def parse_sms_xml(xml_file):
    """
    Parse SMS XML file and convert to JSON objects (list of dictionaries)
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        transactions = []
        
        for idx, sms in enumerate(root.findall('.//sms'), start=1):
            transaction = {
                'id': idx,
                'type': sms.get('type', ''),
                'amount': sms.get('amount', ''),
                'sender': sms.get('sender', ''),
                'receiver': sms.get('receiver', ''),
                'timestamp': sms.get('timestamp', ''),
                'body': sms.get('body', ''),
                'address': sms.get('address', '')
            }
            transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []

def save_to_json(transactions, output_file='transactions.json'):
    """
    Save transactions to JSON file
    """
    with open(output_file, 'w') as f:
        json.dump(transactions, f, indent=2)
    print(f"Saved {len(transactions)} transactions to {output_file}")

if __name__ == "__main__":
    # Parse XML and convert to JSON
    transactions = parse_sms_xml('modified_sms_v2.xml')
    
    # Save to JSON file
    save_to_json(transactions)
    
    # Display first 3 records
    print("\nFirst 3 transactions:")
    for t in transactions[:3]:
        print(json.dumps(t, indent=2))