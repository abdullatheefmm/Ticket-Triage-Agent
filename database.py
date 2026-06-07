"""
Database module for the Ticket Triage Agent.
Handles SQLite database connection, table initialization, and record insertions.
"""

import os
import json
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def init_db(db_path: str) -> None:
    """
    Initializes the SQLite database and creates the ticket_triage table if it doesn't exist.

    Args:
        db_path (str): Absolute or relative path to the SQLite database file.
    """
    # Ensure the parent directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory at {db_dir}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create ticket_triage table with extra columns for the web UI
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_triage (
                ticket_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                react_log TEXT
            )
        """)
        conn.commit()
        logger.info(f"Initialized SQLite database at {db_path} with table 'ticket_triage'")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database {db_path}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def insert_ticket(
    db_path: str,
    ticket_id: str,
    title: str,
    description: str,
    category: str,
    priority: str,
    reasoning: str,
    react_log_json: str
) -> bool:
    """
    Inserts or updates a ticket triage classification result in the database.

    Args:
        db_path (str): Path to the SQLite database.
        ticket_id (str): The unique ticket identifier.
        title (str): The ticket title.
        description (str): The ticket description.
        category (str): Classified category.
        priority (str): Classified priority.
        reasoning (str): Reasoning for classification decisions.
        react_log_json (str): JSON string representing ReAct thought steps.

    Returns:
        bool: True if successful, False otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO ticket_triage (ticket_id, title, description, category, priority, reasoning, react_log)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, title, description, category, priority, reasoning, react_log_json)
        )
        conn.commit()
        logger.debug(f"Inserted/updated ticket {ticket_id} in database")
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to insert ticket {ticket_id} into database: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_all_tickets(db_path: str) -> list:
    """
    Queries and returns all tickets from the SQLite database.

    Args:
        db_path (str): Path to the SQLite database.

    Returns:
        list: A list of dicts representing each ticket triage entry.
    """
    conn = None
    tickets = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_triage")
        rows = cursor.fetchall()
        for r in rows:
            tickets.append({
                "ticket_id": r["ticket_id"],
                "title": r["title"],
                "description": r["description"],
                "category": r["category"],
                "priority": r["priority"],
                "reasoning": r["reasoning"],
                "react_log": json.loads(r["react_log"]) if r["react_log"] else []
            })
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch tickets from database: {e}")
    finally:
        if conn:
            conn.close()
    return tickets

