# MoMo Transaction Analytics Platform

## Team Information
**Team Name:** Team 12

**Team Members:**
- David Muotoh-Francis - [@davidmuotoh](https://github.com/davidmuo) - Developer and designer
- Christian MPANO - [@Christian-pprogrammer](https://github.com/Christian-pprogrammer) - Developer
- Liata Ornella Sifa - [Liata-Ornella](https://github.com/Liata-Ornella) - Developer
- Kenia Umutoni - [@kenia-bit](https://github.com/Kenia-bit) - Developer
- Nathanaella Hirwa - [@NathanaellaHirwa](https://github.com/NathanaellaHirwa) - Developer

---

## Project Description
The **MoMo Transaction Analytics Platform** is a data pipeline and visualization system that processes Mobile Money transaction data from XML files. The system extracts transactions, cleans and normalizes the data, categorizes each transaction type, stores everything in a SQLite database, and displays insights through an interactive web dashboard with charts and statistics.

---

## Project Links
- **Architecture Diagram (Miro):** [View Diagram](https://miro.com/welcomeonboard/Zzk0Y0JLSHUzeWhUblhwMEtOdHU0bjBCc2cvekovazIwSVFJZ0pabHlNaXRnckttd3ZkWFZtRGlMUTg2SFd3MkxSbTI3UVJGZXpXWGpSaGZhNzZIbzNmcERaOXhkcTN4SmtweG1WUXU4OG5aUjNzWCt2SEo5MWdMRWM4MWpCWDVyVmtkMG5hNDA3dVlncnBvRVB2ZXBnPT0hdjE=?share_link_id=428529003251)
- **Scrum Board (Trello):** [View Board](https://trello.com/invite/b/6966a43653d8efd3311e4241/ATTIaa5ae89ef53cfc0232a2589611e385a87625231C/momo-analytics-platform)

---

## Week 2: Database Design & Implementation
📁 **Location:** `/database`

- Designed normalized database schema (3NF)
- Created ERD with 9 entities and proper relationships
- Resolved M:N relationship between users and transactions using junction table
- JSON schema examples for all entities
- SQL setup script with constraints, triggers, and indexes

**Files:**
```
database/
├── docs/                   # ERD diagram and documentation
├── week 2 screenshots/     # API screenshots
├── database_setup.sql      # MySQL schema with constraints, triggers, indexes
├── json_examples.json      # Sample JSON data for entities
└── json_schemas.json       # JSON schema definitions
```

**Database Entities:**
| Entity | Description |
|--------|-------------|
| users | All transaction parties (individuals, merchants, agents) |
| transactions | Parsed transaction records from SMS |
| transaction_categories | Classification of transaction types |
| transaction_parties | Junction table resolving M:N relationship |
| sms_raw_data | Original SMS messages for audit |
| system_logs | Audit and processing logs |
| balance_history | Balance tracking over time |

---

## Technology Stack

**Backend:**
- Python 3.8+
- SQLite / MySQL
- SQLAlchemy (ORM)

**Frontend:**
- HTML/CSS/JavaScript
- Chart.js (Visualizations)

---

## Setup Instructions
```bash
# Clone repository
git clone https://github.com/davidmuo/MoMo-Transaction-Analytics-Platform.git
cd MoMo-Transaction-Analytics-Platform
```

### Database Setup
```bash
cd database
# Import database_setup.sql into MySQL Workbench
# Or use SQLite with the provided schema
```

---

## Project Status
✅ Week 2: Database Design - Complete  
🚧 Week 3: Coming soon

---

## License
This project is for educational purposes at African Leadership University.
