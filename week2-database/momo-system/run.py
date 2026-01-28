#!/usr/bin/env python3
import os
import sys
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def setup():
    from database.models import init_db, get_session, seed_categories
    
    db_file = os.path.join(ROOT, 'momo_sms.db')
    print(f"Setting up database: {db_file}")
    
    engine = init_db(f"sqlite:///{db_file}")
    session = get_session(engine)
    
    cats = seed_categories(session)
    print(f"Added {len(cats)} categories")
    
    session.close()
    print("Done!")


def parse(xml_path):
    from database.models import init_db, get_session, seed_categories
    from parser.sms_parser import MoMoSmsParser
    
    db_file = os.path.join(ROOT, 'momo_sms.db')
    engine = init_db(f"sqlite:///{db_file}")
    session = get_session(engine)
    seed_categories(session)
    
    print(f"Parsing: {xml_path}")
    p = MoMoSmsParser(session)
    stats = p.parse_xml_file(xml_path)
    
    print("\n" + "="*50)
    print(f"Total: {stats['total']}")
    print(f"Parsed: {stats['parsed']} ({stats['parsed']/stats['total']*100:.1f}%)")
    print(f"Failed: {stats['failed']}")
    print("\nBy type:")
    for t, n in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")
    print("="*50)
    
    session.close()


def serve():
    from api.app import app
    
    print("\n" + "="*50)
    print("Starting API server")
    print("URL: http://localhost:5000")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)


def main():
    parser = argparse.ArgumentParser(description='MoMo SMS System')
    parser.add_argument('cmd', choices=['setup', 'parse', 'serve', 'all'], help='what to do')
    parser.add_argument('--xml', '-x', help='path to xml file')
    
    args = parser.parse_args()
    
    if args.cmd == 'setup':
        setup()
    elif args.cmd == 'parse':
        xml = args.xml or 'modified_sms_v2__2_.xml'
        if not os.path.exists(xml):
            xml = input("xml path: ").strip()
        parse(xml)
    elif args.cmd == 'serve':
        serve()
    elif args.cmd == 'all':
        setup()
        xml = args.xml or 'modified_sms_v2__2_.xml'
        if os.path.exists(xml):
            parse(xml)
        else:
            print(f"no xml file found at {xml}, skipping parse")
        serve()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage:")
        print("  python run.py setup        - init db")
        print("  python run.py parse -x FILE - parse xml")
        print("  python run.py serve        - start api")
        print("  python run.py all -x FILE  - do everything")
    else:
        main()