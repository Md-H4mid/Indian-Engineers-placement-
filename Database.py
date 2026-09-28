import os
import pandas as pd
from sqlalchemy import create_engine, text

# --- configure your MySQL workbench ---
db_user = "root"
db_password = "ROOT"
db_host = "localhost"
db_port = "3306"
db_name = "Campus_db"
CSV_PATH = r"C:\FILE LOCATION"

default_database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}"
database_url = f"{default_database_url}/{db_name}"
engine = create_engine(database_url)


def ensure_database() -> None:
    """Create the target database if it does not exist."""
    default_engine = create_engine(default_database_url)
    with default_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
    default_engine.dispose()
    global engine
    engine = create_engine(database_url)


def create_indexes() -> None:
    """Create safe indexes on the imported table."""
    index_defs = {
        "idx_tier": "college_tier(50)",
        "idx_branch": "branch(50)",
        "idx_placement": "placement_status(20)",
        "idx_cgpa": "CGPA",
        "idx_dsa": "DSA_Problems_Solved",
    }

    with engine.connect() as conn:
        for idx_name, column_expr in index_defs.items():
            try:
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON students ({column_expr})")
                )
            except Exception:
                pass
        conn.commit()


def init_db(csv_path: str = CSV_PATH) -> None:
    """Clean raw data and prepare it for MySQL import."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at {csv_path}")

    ensure_database()
    df = pd.read_csv(csv_path)

    if "open_source_Contributions" in df.columns:
        df["open_source_Contributions"] = df["open_source_Contributions"].fillna(
            df["open_source_Contributions"].median()
        )

    if "Linkedin_activity_score" in df.columns:
        df["Linkedin_activity_score"] = df["Linkedin_activity_score"].fillna(
            df["Linkedin_activity_score"].median()
        )

    df.to_sql("students", con=engine, if_exists="replace", index=False)
    create_indexes()
    print("Data Successfully Loaded and Indexed in MySQL Workbench")


def run_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """Runs a query against MySQL using SQLAlchemy."""
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)


if __name__ == "__main__":
    init_db()
