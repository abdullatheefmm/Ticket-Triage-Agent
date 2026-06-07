# Ticket Triage Agent

An AI-powered support ticket classification system built in Python. The system reads support tickets from JSON files, classifies each ticket into a predefined category and priority level, provides detailed reasoning for its decisions using a **ReAct-style workflow** (Thought -> Action -> Observation), and stores the results in both a CSV file and a SQLite database.

It supports intelligent classification via the **OpenAI API** and automatically falls back to a robust, rules-based **keyword classifier** if the API key is not configured.

---

## Features

- **Automated Batch Processing**: Reads and processes all JSON support tickets located in the `tickets/` directory on startup.
- **ReAct-style Reasoning**: Prints sequential logs detailing the agent's thought process, classification action, supporting evidence, priority action, and business impact observation.
- **Interactive Web Dashboard**: A premium, responsive dark-mode glassmorphic single-page web dashboard built with vanilla web technologies (HTML/CSS/JS) served on `http://127.0.0.1:8000`.
- **Dynamic Real-Time Triage**: Submit custom tickets via the web interface form and watch the ReAct agent process the ticket in real-time in the terminal-style console.
- **Dual Storage Output**:
  - Appends and saves results to `output/results.csv`.
  - Saves records in a local SQLite database at `database/tickets.db` under the `ticket_triage` table.
- **Robust Error Handling**: Gracefully detects, logs, and skips invalid JSON formatting or missing fields, ensuring the process continues uninterrupted.
- **Terminal & File Reports**: Prints a clean dashboard summary in the terminal and saves it to `output/report.txt`.
- **Fallback Capability**: Operates out-of-the-box using the built-in rule-based keyword classifier if `OPENAI_API_KEY` is not present in environment variables.

---

## Folder Structure

```text
Ticket/
│
├── tickets/                # Input folder containing JSON support tickets
│   ├── T001.json
│   ├── T002.json
│   └── ...
│
├── static/                 # Web interface files
│   └── index.html          # Interactive dark-mode dashboard
│
├── output/                 # Output folder for results and summaries
│   ├── results.csv         # Processed ticket classifications in CSV
│   └── report.txt          # Saved terminal summary report
│
├── database/               # Database storage
│   └── tickets.db          # SQLite Database containing triage records
│
├── agent.py                # ReAct agent implementation (OpenAI / Fallback)
├── database.py             # SQLite operations (Initialization, Insertion, Querying)
├── main.py                 # Core orchestrator, FastAPI app, and server
├── requirements.txt        # Python dependency list
├── triage.log              # Log file capturing info, warnings, and errors
└── README.md               # Project documentation
```

---

## Installation Steps

1. **Clone the Repository**:
   Navigate to the project directory:
   ```bash
   cd Ticket
   ```

2. **Set up a Virtual Environment (Optional but Recommended)**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (Optional for AI Mode)**:
   Create a `.env` file in the root directory and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   *Note: If no `.env` is created or no API key is specified, the application will automatically run using the rule-based keyword classifier fallback.*

---

## Usage Instructions

Run the main orchestrator script:
```bash
python main.py
```

On execution, the script will:
1. Initialize the `tickets/`, `output/`, `database/`, and `static/` folders.
2. If `tickets/` is empty, it will **automatically generate 20 sample tickets** representing all categories and priorities, plus one invalid JSON ticket to demonstrate parsing error handling.
3. Process all tickets in the folder, printing the ReAct workflow logs to the terminal.
4. Save the results to `output/results.csv` and `database/tickets.db`.
5. Start a local FastAPI server on `http://127.0.0.1:8000` and **automatically open the web dashboard** in your default web browser.

### Interactive Dashboard Walkthrough
- **KPI Metrics Cards**: Look at the glowing cards at the top showing total processed tickets, plus counts and percentages for Bugs, Billing, and Features.
- **Triage Console**: Type a custom ticket title and description into the form, click **Triage Ticket**, and watch the terminal window output the agent's thought process step-by-step in real-time.
- **Interactive Table**: Browse, search (by ID, title, or reasoning), and filter tickets by category or priority.
- **Visual ReAct Logs**: Click the "Details" (eye icon) button on any ticket row to open a modal showing the full ticket description and the exact step-by-step ReAct reasoning steps (Thoughts, Actions, Observations, Final Answer) highlighted with custom styling and color-coded icons.

---

## Sample Input and Output

### Sample Input File (`tickets/T001.json`)
```json
{
  "ticket_id": "T001",
  "title": "Payment deducted twice",
  "description": "Money was charged twice from my bank account for a single subscription transaction. Please refund the extra charge."
}
```

### Console Output (ReAct Workflow)
```text
============================================================
TRIAGING TICKET: T001
Title: Payment deducted twice
============================================================
Thought:
Analyzing ticket T001: 'Payment deducted twice'. Examining ticket title and description for keywords relating to Billing, Bugs, or Features.

Action:
Determine Category [Bug, Feature, Billing, or Other] -> Billing

Observation:
Found billing-related keywords: pay, charge, subscription.

Action:
Determine Priority [P1, P2, P3, or P4] -> P1

Observation:
Billing discrepancy involves potential double charges or unauthorized transactions, creating critical financial impact.

Final Answer:
{
  "category": "Billing",
  "priority": "P1",
  "reasoning": "Categorized as Billing based on matching keywords. Priority set to P1 due to estimated business impact: Billing discrepancy involves potential double charges or unauthorized transactio..."
}
============================================================
```

### Processed Output CSV Record (`output/results.csv`)
```csv
ticket_id,title,category,priority,reasoning
T001,Payment deducted twice,Billing,P1,Categorized as Billing based on matching keywords. Priority set to P1 due to estimated business impact...
```

---

## Future Enhancements

1. **API Integration expansion**: Add support for other LLM models (e.g. Google Gemini, Anthropic Claude).
2. **Email Integration**: Auto-ingest tickets directly from support email addresses.
3. **Auto-Assignment**: Route tickets directly to engineering, billing, or product managers based on category and priority.
