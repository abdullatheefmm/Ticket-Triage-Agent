"""
Agent module for the Ticket Triage Agent.
Implements a ReAct-style workflow for ticket classification.
Supports OpenAI API (with dotenv) and a robust keyword-based fallback classifier.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# Try importing OpenAI, handle failure gracefully
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TicketTriageAgent:
    """
    AI Agent that classifies support tickets into categories and priorities
    using a ReAct-style (Thought -> Action -> Observation) workflow.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.use_openai = OPENAI_AVAILABLE and bool(self.api_key)
        
        if self.use_openai:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Falling back to keyword classifier.")
                self.use_openai = False
        else:
            if not OPENAI_AVAILABLE:
                logger.info("OpenAI package not installed. Using keyword-based classifier.")
            else:
                logger.info("OPENAI_API_KEY not found. Using keyword-based classifier.")

    def triage_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Triages a single support ticket by determining its category, priority, and reasoning.

        Args:
            ticket (Dict[str, Any]): A dictionary containing 'ticket_id', 'title', and 'description'.

        Returns:
            Dict[str, Any]: The classification results containing ticket_id, category, priority, reasoning, and react_log.
        """
        ticket_id = ticket.get("ticket_id", "UNKNOWN")
        title = ticket.get("title", "")
        description = ticket.get("description", "")

        print(f"\n{'='*60}")
        print(f"TRIAGING TICKET: {ticket_id}")
        print(f"Title: {title}")
        print(f"{'='*60}")

        if self.use_openai:
            try:
                return self._triage_with_openai(ticket_id, title, description)
            except Exception as e:
                logger.error(f"OpenAI triage failed for ticket {ticket_id}: {e}. Trying fallback classifier.")
                print(f"[Warning] OpenAI API call failed. Using fallback keyword classifier...")
                return self._triage_with_fallback(ticket_id, title, description)
        else:
            return self._triage_with_fallback(ticket_id, title, description)

    def _triage_with_openai(self, ticket_id: str, title: str, description: str) -> Dict[str, Any]:
        """
        Performs triage using OpenAI API with a structured prompt enforcing ReAct formatting.
        """
        system_prompt = (
            "You are an expert customer support agent. Classify the ticket into a category and priority level.\n\n"
            "Categories:\n"
            "- Bug (technical errors, crashes, broken functionality)\n"
            "- Feature (requests for new features, enhancements, integrations)\n"
            "- Billing (payment issues, charges, subscription plans, refunds)\n"
            "- Other (general questions, feedbacks, unspecified issues)\n\n"
            "Priority Levels:\n"
            "- P1 = Critical (system outage, security vulnerability, payment errors, complete blocker)\n"
            "- P2 = High (important core feature broken, major annoyance, no easy workaround)\n"
            "- P3 = Medium (non-critical bug, feature request, general question with moderate impact)\n"
            "- P4 = Low (cosmetic bugs, typo reports, simple questions, low business impact)\n\n"
            "You MUST follow this exact ReAct reasoning process and print each step exactly as labeled:\n"
            "Thought: <your thought process analyzing the ticket title and description>\n"
            "Action: Determine Category [Bug, Feature, Billing, or Other]\n"
            "Observation: <supporting evidence for the chosen category from the ticket>\n"
            "Action: Determine Priority [P1, P2, P3, or P4]\n"
            "Observation: <business impact and urgency assessment>\n"
            "Final Answer:\n"
            "{\n"
            '  "category": "<chosen category>",\n'
            '  "priority": "<chosen priority>",\n'
            '  "reasoning": "<short sentence explaining the decision based on your actions and observations>"\n'
            "}"
        )

        user_content = f"Ticket ID: {ticket_id}\nTitle: {title}\nDescription: {description}"

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )

        response_text = response.choices[0].message.content or ""
        
        # Print the ReAct workflow output to console
        print(response_text)

        # Parse output for category, priority, reasoning
        category, priority, reasoning = self._parse_react_output(response_text, title, description)
        react_log = self._parse_react_log(response_text)

        return {
            "ticket_id": ticket_id,
            "category": category,
            "priority": priority,
            "reasoning": reasoning,
            "react_log": react_log
        }

    def _triage_with_fallback(self, ticket_id: str, title: str, description: str) -> Dict[str, Any]:
        """
        Rule-based classifier that simulates the exact ReAct steps using keywords.
        """
        title_lower = title.lower()
        desc_lower = description.lower()
        combined = f"{title_lower} {desc_lower}"

        # 1. Thought Process
        thought = (
            f"Analyzing ticket {ticket_id}: '{title}'. "
            f"Examining ticket title and description for keywords relating to Billing, Bugs, or Features."
        )
        print(f"Thought:\n{thought}\n")

        # 2. Category Decision
        billing_keywords = ["pay", "charge", "refund", "subscription", "deduct", "invoice", "price", "credit card", "billing", "cost", "fee", "transaction", "money", "card"]
        bug_keywords = ["crash", "error", "broken", "bug", "fail", "not working", "glitch", "freeze", "blank screen", "issue", "unexpected", "doesn't work", "loading", "incorrect", "exception", "db error", "slow", "lag", "timeout"]
        feature_keywords = ["suggest", "improve", "would be nice", "add support", "new feature", "request", "want to see", "integrate", "enhancement", "allow me to", "integrate with"]

        matched_billing = [kw for kw in billing_keywords if kw in combined]
        matched_bug = [kw for kw in bug_keywords if kw in combined]
        matched_feature = [kw for kw in feature_keywords if kw in combined]

        if matched_billing:
            category = "Billing"
            evidence = f"Found billing-related keywords: {', '.join(matched_billing[:3])}."
        elif matched_bug:
            category = "Bug"
            evidence = f"Found bug-related keywords: {', '.join(matched_bug[:3])}."
        elif matched_feature:
            category = "Feature"
            evidence = f"Found feature/enhancement keywords: {', '.join(matched_feature[:3])}."
        else:
            category = "Other"
            evidence = "No specific category keywords found. Defaulting to general support."

        print(f"Action:\nDetermine Category [Bug, Feature, Billing, or Other] -> {category}\n")
        print(f"Observation:\n{evidence}\n")

        # 3. Priority Decision
        critical_keywords = ["security", "data loss", "cannot log in", "security breach", "vulnerability", "leak", "down", "outage", "leakage", "hacked", "stolen", "twice"]
        high_keywords = ["urgent", "fail", "error", "crash", "freeze", "cannot", "unable", "broken", "failing", "db error", "payment deducted"]

        matched_critical = [kw for kw in critical_keywords if kw in combined]
        matched_high = [kw for kw in high_keywords if kw in combined]

        if category == "Billing":
            if any(kw in combined for kw in ["twice", "stolen", "unauthorized", "charge", "refund"]):
                priority = "P1"
                impact = "Billing discrepancy involves potential double charges or unauthorized transactions, creating critical financial impact."
            else:
                priority = "P2"
                impact = "General billing or subscription concern affecting user account access."
        elif category == "Bug":
            if matched_critical:
                priority = "P1"
                impact = "Bug involves high-severity security, login failure, or potential data loss."
            elif matched_high:
                priority = "P2"
                impact = "Core system function is broken or highly degraded, affecting workflow."
            else:
                priority = "P3"
                impact = "Minor bug with a workaround or low impact on system operations."
        elif category == "Feature":
            if "integrate" in combined or "urgent" in combined:
                priority = "P3"
                impact = "Feature request has moderate impact or potential business integration value."
            else:
                priority = "P4"
                impact = "Standard feature request or enhancement suggestion for future consideration."
        else:
            priority = "P4"
            impact = "General inquiry with low urgency and no direct impact on service availability."

        print(f"Action:\nDetermine Priority [P1, P2, P3, or P4] -> {priority}\n")
        print(f"Observation:\n{impact}\n")

        # 4. Final Answer
        reasoning = f"Categorized as {category} based on matching keywords. Priority set to {priority} due to estimated business impact: {impact[:80]}..."
        
        final_answer = {
            "category": category,
            "priority": priority,
            "reasoning": reasoning
        }
        print("Final Answer:")
        print(json.dumps(final_answer, indent=2))
        print(f"{'='*60}\n")

        react_log = [
            {"step": "Thought", "text": thought},
            {"step": "Action", "text": f"Determine Category [Bug, Feature, Billing, or Other] -> {category}"},
            {"step": "Observation", "text": evidence},
            {"step": "Action", "text": f"Determine Priority [P1, P2, P3, or P4] -> {priority}"},
            {"step": "Observation", "text": impact},
            {"step": "Final Answer", "text": json.dumps(final_answer, indent=2)}
        ]

        return {
            "ticket_id": ticket_id,
            "category": category,
            "priority": priority,
            "reasoning": reasoning,
            "react_log": react_log
        }

    def _parse_react_output(self, text: str, title: str, description: str) -> Tuple[str, str, str]:
        """
        Parses the OpenAI response text to extract category, priority, and reasoning.
        Falls back to keyword-based heuristics if parsing fails.
        """
        # Look for the final JSON block
        json_match = re.search(r"\{[\s\S]*?\}", text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                category = data.get("category", "").strip().capitalize()
                priority = data.get("priority", "").strip().upper()
                reasoning = data.get("reasoning", "").strip()

                # Validate values
                if category not in ["Bug", "Feature", "Billing", "Other"]:
                    category = "Other"
                if priority not in ["P1", "P2", "P3", "P4"]:
                    priority = "P4"
                if not reasoning:
                    reasoning = "Parsed successfully from LLM output."

                return category, priority, reasoning
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON block in LLM response.")

        # Regex fallback if JSON parsing failed
        category_match = re.search(r"Category:\s*(Bug|Feature|Billing|Other)", text, re.IGNORECASE)
        priority_match = re.search(r"Priority:\s*(P1|P2|P3|P4)", text, re.IGNORECASE)
        reasoning_match = re.search(r"Reasoning:\s*(.*)", text, re.IGNORECASE)

        category = category_match.group(1).capitalize() if category_match else "Other"
        priority = priority_match.group(1).upper() if priority_match else "P4"
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Extracted via regex fallback from LLM output."

        return category, priority, reasoning

    def _parse_react_log(self, text: str) -> list:
        """
        Parses full ReAct log text from LLM into a structured list of steps.
        """
        steps = []
        # Robust pattern matching step tags (Thought, Action, Observation, Final Answer) and their content
        pattern = r"(Thought|Action|Observation|Final Answer)(?:\s*\([^)]*\))?:\s*(.*?)(?=\n(?:Thought|Action|Observation|Final Answer)(?:\s*\([^)]*\))?:|\Z)"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for step_name, content in matches:
            steps.append({
                "step": step_name.strip().title(),
                "text": content.strip()
            })
            
        if not steps:
            steps.append({
                "step": "Final Answer",
                "text": text.strip()
            })
            
        return steps
