"""
Main orchestration module for the Ticket Triage Agent.
Handles startup, directory creation, sample data generation, ticket parsing,
agent invocation, database/CSV storage, logging, reporting, and a FastAPI web server dashboard.
"""

import os
import csv
import json
import logging
import webbrowser
from threading import Timer
from typing import Dict, Any, List

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Import local modules
from agent import TicketTriageAgent
from database import init_db, insert_ticket, get_all_tickets

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("triage.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MainRunner")

# Constants
TICKETS_DIR = "tickets"
OUTPUT_DIR = "output"
DATABASE_DIR = "database"
CSV_PATH = os.path.join(OUTPUT_DIR, "results.csv")
DB_PATH = os.path.join(DATABASE_DIR, "tickets.db")

# FastAPI App initialization
app = FastAPI(
    title="Ticket Triage Agent API",
    description="Backend API for Support Ticket Classification and ReAct Logs",
    version="1.0.0"
)

# Initialize Agent globally
agent = TicketTriageAgent()


class TicketRequest(BaseModel):
    title: str
    description: str


def create_directories() -> None:
    """Creates the folders for input, output, and database if they don't exist."""
    for folder in [TICKETS_DIR, OUTPUT_DIR, DATABASE_DIR, "static"]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            logger.info(f"Created directory: {folder}")


def generate_sample_tickets() -> None:
    """Generates 20 valid JSON sample tickets and 1 invalid JSON sample ticket if tickets/ is empty."""
    if os.path.exists(TICKETS_DIR) and len(os.listdir(TICKETS_DIR)) > 0:
        logger.info(f"Tickets directory '{TICKETS_DIR}' already contains files. Skipping sample generation.")
        return

    logger.info("Generating sample tickets in 'tickets/' directory...")
    
    samples = [
        {
            "ticket_id": "T001",
            "title": "Payment deducted twice",
            "description": "Money was charged twice from my bank account for a single subscription transaction. Please refund the extra charge."
        },
        {
            "ticket_id": "T002",
            "title": "Database connection error on checkout",
            "description": "Getting a 500 error and db error when trying to complete the purchase. Entire checkout is blocked."
        },
        {
            "ticket_id": "T003",
            "title": "Slack integration request",
            "description": "We would love to see Slack integration to receive notifications of new comments and tickets on our team channel."
        },
        {
            "ticket_id": "T004",
            "title": "Typo in checkout header",
            "description": "The checkout page header says 'Proceed to Payement' instead of 'Payment'. Just a small typo."
        },
        {
            "ticket_id": "T005",
            "title": "Cannot log in to my account",
            "description": "Getting infinite spinner on the login screen. It shows error code LOG-999. I cannot access my dashboard."
        },
        {
            "ticket_id": "T006",
            "title": "Annual plan subscription price discrepancy",
            "description": "I was charged $120 instead of the advertised $99 for the annual premium subscription."
        },
        {
            "ticket_id": "T007",
            "title": "Profile avatar upload fails",
            "description": "Fails to upload a 2MB JPEG image. Shows a broken image upload warning without any details."
        },
        {
            "ticket_id": "T008",
            "title": "Dark mode request",
            "description": "It would be nice to have a dark mode toggle to reduce eye strain during night shifts."
        },
        {
            "ticket_id": "T009",
            "title": "API rate limits questions",
            "description": "What are the API rate limits for the free trial vs the professional tier? We cannot find it in docs."
        },
        {
            "ticket_id": "T010",
            "title": "Export CSV button is unresponsive",
            "description": "Clicking the 'Export CSV' button on the dashboard reports list does nothing. No logs or errors shown."
        },
        {
            "ticket_id": "T011",
            "title": "Refund request due to downtime",
            "description": "Our service was down for 5 hours yesterday during peak hours. Requesting a prorated refund/credit to our account."
        },
        {
            "ticket_id": "T012",
            "title": "Multi-factor authentication (MFA) support",
            "description": "Please add support for Google Authenticator or SMS MFA to secure customer logins."
        },
        {
            "ticket_id": "T013",
            "title": "Mobile navigation menu layout issues",
            "description": "On iPhone 13, the navigation links overlap and are unclickable in landscape mode."
        },
        {
            "ticket_id": "T014",
            "title": "Team plan pricing query",
            "description": "Do you offer custom pricing for teams of 50+ users? What features and support SLA are included?"
        },
        {
            "ticket_id": "T015",
            "title": "CRITICAL: API key exposure in console logs",
            "description": "The client application logs the OpenAI API key to the console in debug mode. Security risk of exposure!"
        },
        {
            "ticket_id": "T016",
            "title": "Credit card update fails",
            "description": "Trying to update my Visa card details fails with 'Tokenization error'. Need to pay my invoice by tomorrow."
        },
        {
            "ticket_id": "T017",
            "title": "Bulk data export scheduling feature",
            "description": "We need an option to schedule automated database backups/exports to our S3 bucket weekly."
        },
        {
            "ticket_id": "T018",
            "title": "Severe dashboard latency",
            "description": "The dashboard page takes over 15 seconds to load and shows lag. Timeout errors occur occasionally."
        },
        {
            "ticket_id": "T019",
            "title": "Kudos to the support team",
            "description": "Just wanted to say thanks for the quick help on my billing issues last week! Fantastic support."
        },
        {
            "ticket_id": "T020",
            "title": "Expired password reset link",
            "description": "The password reset link generated by the system is expired immediately after receiving the email. Cannot reset password."
        }
    ]

    # Write valid sample JSON files
    for sample in samples:
        file_path = os.path.join(TICKETS_DIR, f"{sample['ticket_id']}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2)

    # Write one intentionally invalid JSON file to demonstrate robust error handling
    invalid_file_path = os.path.join(TICKETS_DIR, "T021_invalid.json")
    with open(invalid_file_path, "w", encoding="utf-8") as f:
        f.write('{\n  "ticket_id": "T021",\n  "title": "Corrupted Ticket",\n  "description": "Missing ending brackets...')
        
    logger.info(f"Successfully generated {len(samples)} valid tickets and 1 invalid ticket in '{TICKETS_DIR}/'")


def save_to_csv(results: List[Dict[str, Any]]) -> None:
    """Saves a batch of results to the results CSV file, overwriting previous content."""
    try:
        with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ticket_id", "title", "category", "priority", "reasoning"])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "ticket_id": r["ticket_id"],
                    "title": r["title"],
                    "category": r["category"],
                    "priority": r["priority"],
                    "reasoning": r["reasoning"]
                })
        logger.info(f"Successfully wrote {len(results)} results to {CSV_PATH}")
    except Exception as e:
        logger.error(f"Failed to write results to CSV: {e}")


def append_to_csv(ticket_id: str, title: str, category: str, priority: str, reasoning: str) -> None:
    """Appends a single triage record to the results CSV."""
    try:
        file_exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ticket_id", "title", "category", "priority", "reasoning"])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "ticket_id": ticket_id,
                "title": title,
                "category": category,
                "priority": priority,
                "reasoning": reasoning
            })
        logger.info(f"Appended ticket {ticket_id} to CSV")
    except Exception as e:
        logger.error(f"Failed to append ticket {ticket_id} to CSV: {e}")


def display_report(results: List[Dict[str, Any]], invalid_count: int) -> None:
    """Generates and displays a summary report in the terminal and saves it to output/report.txt."""
    total_processed = len(results)
    
    categories = {"Bug": 0, "Feature": 0, "Billing": 0, "Other": 0}
    priorities = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    
    for r in results:
        cat = r.get("category", "Other")
        pri = r.get("priority", "P4")
        if cat in categories:
            categories[cat] += 1
        else:
            categories["Other"] += 1
        if pri in priorities:
            priorities[pri] += 1
        else:
            priorities["P4"] += 1

    report_lines = [
        "============================================================",
        "              TICKET TRIAGE PROCESSING REPORT",
        "============================================================",
        f"Total Tickets Found:      {total_processed + invalid_count}",
        f"Successfully Processed:   {total_processed}",
        f"Failed/Invalid JSON:      {invalid_count}",
        "",
        "Category Breakdown:",
        f" - Bug:                    {categories['Bug']}",
        f" - Billing:                {categories['Billing']}",
        f" - Feature:                {categories['Feature']}",
        f" - Other:                  {categories['Other']}",
        "",
        "Priority Breakdown:",
        f" - P1 (Critical):          {priorities['P1']}",
        f" - P2 (High):              {priorities['P2']}",
        f" - P3 (Medium):            {priorities['P3']}",
        f" - P4 (Low):               {priorities['P4']}",
        "",
        "Storage Details:",
        f" - Log file:               triage.log",
        f" - CSV Output:             {CSV_PATH}",
        f" - SQLite Database:        {DB_PATH}",
        "============================================================"
    ]
    
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save the report to output/report.txt
    report_path = os.path.join(OUTPUT_DIR, "report.txt")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        logger.info(f"Saved classification report to {report_path}")
    except Exception as e:
        logger.error(f"Failed to write report to file: {e}")


def get_next_ticket_id() -> str:
    """Calculates the next ticket ID in sequence (e.g. T021, T022)."""
    tickets = get_all_tickets(DB_PATH)
    max_num = 0
    for t in tickets:
        t_id = t.get("ticket_id", "")
        if t_id.startswith("T") and t_id[1:].isdigit():
            num = int(t_id[1:])
            if num > max_num:
                max_num = num
    return f"T{max_num + 1:03d}"


# =====================================================================
# FastAPI Server Endpoints
# =====================================================================

@app.get("/")
def read_root():
    """Serves the static index.html dashboard file at root URL."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Dashboard index.html not found.")


@app.get("/api/tickets")
def fetch_all_tickets_endpoint():
    """API endpoint to get all triaged tickets from the database."""
    tickets = get_all_tickets(DB_PATH)
    return tickets


@app.get("/api/stats")
def get_dashboard_stats():
    """API endpoint to query aggregates for UI charts and cards."""
    tickets = get_all_tickets(DB_PATH)
    total = len(tickets)
    categories = {"Bug": 0, "Feature": 0, "Billing": 0, "Other": 0}
    priorities = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for t in tickets:
        cat = t.get("category", "Other")
        pri = t.get("priority", "P4")
        if cat in categories:
            categories[cat] += 1
        if pri in priorities:
            priorities[pri] += 1
            
    return {
        "total": total,
        "categories": categories,
        "priorities": priorities
    }


@app.post("/api/triage")
def triage_custom_ticket(req: TicketRequest):
    """API endpoint to triage a new custom submitted ticket in real-time."""
    if not req.title.strip() or not req.description.strip():
        raise HTTPException(status_code=400, detail="Title and description cannot be empty.")
        
    next_id = get_next_ticket_id()
    ticket_payload = {
        "ticket_id": next_id,
        "title": req.title.strip(),
        "description": req.description.strip()
    }
    
    try:
        # Run classification agent
        result = agent.triage_ticket(ticket_payload)
        
        # Save to SQLite
        db_success = insert_ticket(
            DB_PATH,
            next_id,
            req.title.strip(),
            req.description.strip(),
            result["category"],
            result["priority"],
            result["reasoning"],
            json.dumps(result["react_log"])
        )
        if not db_success:
            logger.error(f"Failed to record ticket {next_id} to database.")
            
        # Append to CSV
        append_to_csv(
            next_id,
            req.title.strip(),
            result["category"],
            result["priority"],
            result["reasoning"]
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to triage custom ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Triage process failed: {str(e)}")


def run_batch_triage() -> int:
    """Runs the initial batch processing on tickets folder JSONs."""
    logger.info("Executing initial offline batch ticket triage...")
    processed_results = []
    invalid_count = 0
    
    files = sorted([f for f in os.listdir(TICKETS_DIR) if f.endswith(".json")])
    if not files:
        logger.warning(f"No ticket JSON files found in directory '{TICKETS_DIR}'")
        return 0
        
    logger.info(f"Found {len(files)} ticket file(s) in '{TICKETS_DIR}'. Starting triage processing...")
    
    for filename in files:
        file_path = os.path.join(TICKETS_DIR, filename)
        logger.info(f"Processing ticket file: {filename}")
        
        # Read and validate JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                ticket_data = json.load(f)
        except json.JSONDecodeError as jde:
            logger.error(f"Invalid JSON file {filename}: {jde}. Skipping.")
            invalid_count += 1
            continue
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}. Skipping.")
            invalid_count += 1
            continue

        # Check required fields
        ticket_id = ticket_data.get("ticket_id")
        title = ticket_data.get("title")
        description = ticket_data.get("description")
        
        if not ticket_id or not title or not description:
            logger.error(f"Ticket file {filename} is missing required fields (ticket_id, title, description). Skipping.")
            invalid_count += 1
            continue
            
        # Call AI Agent
        try:
            result = agent.triage_ticket(ticket_data)
            
            full_record = {
                "ticket_id": result["ticket_id"],
                "title": title,
                "category": result["category"],
                "priority": result["priority"],
                "reasoning": result["reasoning"]
            }
            processed_results.append(full_record)
            
            # Save to SQLite database (with description & react logs JSON stringified)
            insert_ticket(
                DB_PATH,
                full_record["ticket_id"],
                title,
                description,
                full_record["category"],
                full_record["priority"],
                full_record["reasoning"],
                json.dumps(result["react_log"])
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred triaging ticket {ticket_id}: {e}")
            invalid_count += 1

    # Save initial batch results to CSV
    save_to_csv(processed_results)
    
    # Display & Save summary report
    display_report(processed_results, invalid_count)
    return len(processed_results)


def start_server():
    """Starts the uvicorn API server and launches the browser dashboard."""
    def open_browser():
        logger.info("Opening dashboard in web browser...")
        webbrowser.open("http://127.0.0.1:8000")
        
    # Launch browser after 1.5s (giving Uvicorn time to start)
    Timer(1.5, open_browser).start()
    
    # Run server
    logger.info("Starting web dashboard server at http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


def main() -> None:
    """Main execution orchestrator."""
    # 1. Initialize environment directories
    create_directories()
    
    # 2. Setup SQLite DB
    init_db(DB_PATH)
    
    # 3. Generate tickets if empty
    generate_sample_tickets()
    
    # 4. Process all tickets offline to initialize outputs
    run_batch_triage()
    
    # 5. Launch the Web Console Server
    start_server()


if __name__ == "__main__":
    main()
