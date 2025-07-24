from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.database import Base  
from app.models.user_models import User, Staff, UserroleAssignment, Role


def test_postgresql_connection_orm(user, password, host, port, database):
    try:
        # Create the SQLAlchemy engine
        DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(DATABASE_URL, echo=True)

        # Test the connection
        with engine.connect() as connection:
            # Use `text` to execute raw SQL queries in SQLAlchemy 2.0+
            result = connection.execute(text("SELECT version();"))
            db_version = result.fetchone()
            print("Connection successful!")
            print("PostgreSQL Database Version:", db_version[0])

        # Create or update the tables from users and timesheet models
        create_tables(engine)

        # Create a session (optional, for further ORM interactions)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        print("Session established successfully!")

        # Close the session
        session.close()

    except OperationalError as e:
        print("Error connecting to PostgreSQL:", e)

def create_tables(engine):
    """
    Create or update the tables from users and timesheet models.
    """

    # Create all tables in the engine
    Base.metadata.create_all(engine)
    print("Tables created or updated successfully!")

# def update_table_columns(engine, table_name, existing_columns):
#     """
#     Updates a table's structure by adding missing columns or updating their definitions.
#     """
#     with engine.connect() as connection:
#         if table_name == "timesheet_config":
#             # Check and add/update necessary columns in the `timesheet_config` table
#             if "is_open" not in existing_columns:
#                 connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN is_open BOOLEAN DEFAULT True;"))
#                 print(f"Column 'is_open' added to {table_name}.")
#             if "open_date" not in existing_columns:
#                 connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN open_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
#                 print(f"Column 'open_date' added to {table_name}.")
#             if "close_date" not in existing_columns:
#                 connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN close_date TIMESTAMP DEFAULT '2025-01-31';"))
#                 print(f"Column 'close_date' added to {table_name}.")
#             if "created_by" not in existing_columns:
#                 connection.execute(text(f"""
#                     ALTER TABLE {table_name} ADD COLUMN created_by UUID NOT NULL;
#                     ALTER TABLE {table_name} ADD CONSTRAINT fk_created_by FOREIGN KEY (created_by) REFERENCES staffs(id) ON DELETE SET NULL;
#                 """))
#                 print(f"Column 'created_by' and foreign key constraint added to {table_name}.")

# Replace the following with your actual PostgreSQL server credentials
user = "postgres"
password = "Royal  2023"
host = "localhost"
port = 5432
database = "Roster"

test_postgresql_connection_orm(user, password, host, port, database)
