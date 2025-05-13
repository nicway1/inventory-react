# Inventory Management System

## Description

This is a web-based inventory management system built with Flask. It allows users to track assets (like computers, laptops) and accessories, manage their status, assign them to users or customers, and maintain a history of changes and transactions. The system includes role-based access control (Super Admin, Country Admin, Supervisor, Client, User) and provides features for importing/exporting data, managing users and customers, and tracking tickets related to assets.

## Features

*   **Asset Management:** Track detailed information about tech assets including serial number, model, type, specifications, status, location, PO number, receiving date, condition, etc.
*   **Accessory Management:** Manage stock levels (total and available) for accessories like keyboards, chargers, etc.
*   **User Roles:** Supports multiple user roles (Super Admin, Country Admin, Supervisor, Client, User) with varying permissions.
*   **Customer Management:** Manage customer users and assign assets to them.
*   **Status Tracking:** Track asset status (In Stock, Deployed, Shipped, Archived, Disposed, etc.) and condition.
*   **History & Transactions:** Maintain a detailed history log for changes made to assets and accessories, and track transactions (checkout, checkin).
*   **Import/Export:** Bulk import inventory data from CSV files and export current inventory data.
*   **Filtering & Search:** Filter and search inventory based on various criteria like company, model, country, status.
*   **Ticketing System:** Basic integration for tracking tickets associated with assets.
*   **Shipment Tracking:** Functionality for managing shipments and tracking numbers.
*   **Data Integrity Checks:** Includes scripts for checking duplicates and managing database schema.
*   **Admin Dashboard:** Provides administrative functions for user management, system history viewing, and data management.

## Technologies Used

*   **Backend:** Python, Flask
*   **Database:** SQLAlchemy (with SQLite as the default local database)
*   **Templating:** Jinja2
*   **Frontend:** HTML, Tailwind CSS (implied by class names in templates), JavaScript
*   **Authentication:** Flask-Login
*   **Migrations:** Flask-Migrate, Alembic (implied by `migrations` directory and `alembic.ini`)
*   **Forms:** Flask-WTF (for CSRF protection)
*   **Email:** Flask-Mail
*   **Other Libraries:** Pandas (for CSV import), Flask-Cors

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd inventory
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment Variables (Optional):**
    *   Set `SECRET_KEY` for Flask session security.
    *   Set `DATABASE_URL` if using a database other than the default `sqlite:///inventory.db`.
    *   Configure `MAIL_USERNAME` and `MAIL_PASSWORD` (Gmail App Password recommended) if email functionality is needed.
5.  **Initialize the database:**
    *   The application attempts to initialize the database and create a default admin user (`admin`/`admin123`) on the first run if `inventory.db` doesn't exist.
    *   Alternatively, you might need to run migration scripts if using Flask-Migrate/Alembic:
        ```bash
        # Assuming Flask-Migrate is set up
        flask db init  # Only if migrations folder doesn't exist
        flask db migrate -m "Initial migration"
        flask db upgrade
        ```
    *   Run `init_admin.py` if needed to create the initial admin user separately:
        ```bash
        python init_admin.py
        ```

## Usage

1.  **Run the Flask development server:**
    ```bash
    python app.py
    ```
2.  **Access the application:** Open your web browser and go to `http://127.0.0.1:5001` (or the port indicated if 5001 is busy).
3.  **Login:** Use the default admin credentials (`admin`/`admin123`) or credentials for other created users.

## Database

*   The application uses SQLAlchemy ORM to interact with the database.
*   The default database is SQLite (`inventory.db`).
*   Database models are defined in the `models/` directory.
*   Migrations are likely handled by Flask-Migrate/Alembic (check the `migrations/` directory).

## Configuration

*   Core application settings are in `app.py`, using environment variables or default values.
*   Database connection is configured via `SQLALCHEMY_DATABASE_URI`.
*   Email settings (`MAIL_*`) are configured in `app.py`.
*   Secret key for session management (`SECRET_KEY`).

## Utility Scripts

The project contains several utility scripts in the root directory for database management, data fixing, and feature updates:

*   `init_db.py`: Initializes the database schema.
*   `init_admin.py`: Creates the initial super admin user.
*   `recreate_db.py`: Potentially drops and recreates the database (use with caution).
*   `migrate_db.py` / `run_migrations.py`: Scripts related to database migrations.
*   `update_*.py` / `fix_*.py` / `add_*.py`: Various scripts created during development to modify schema, fix data, or add specific features (e.g., `update_asset_model.py`, `fix_asset_relationship.py`, `clean_none_none_history.py`). Review script descriptions before running.

## Deployment (PythonAnywhere Example)

1.  Ensure all necessary code and scripts are pushed to your Git repository.
2.  SSH into your PythonAnywhere account.
3.  Navigate to the project directory (e.g., `/home/yourusername/inventory`).
4.  Pull the latest changes: `git pull`
5.  Run any necessary database migration or update scripts (e.g., `python update_asset_model.py`).
6.  Reload the web application via the PythonAnywhere web tab or by touching the WSGI configuration file: `touch /var/www/yourusername_pythonanywhere_com_wsgi.py`.
