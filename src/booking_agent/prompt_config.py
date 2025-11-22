##=======================================================================
# SETUP : Define global variables for parser and prompt template
##=======================================================================

# from booking_agent.schemas import AgentState, BookingRequest

REQUEST_TEMPLATE = """Role: You are an environment booking assistant. Extract environment booking information from user requests and return ONLY a JSON object.

Current Date: {current_date}
Current Time: {current_time}

IMPORTANT DATE HANDLING:
- When user says "today" → use {current_date}
- When user says "tomorrow" → calculate {current_date} + 1 day
- When user says "now" or "current time" → use {current_time}
- Always convert dates to YYYY-MM-DD format
- Always convert times to HH:MM:SS AM/PM format

REQUIRED FIELDS:
- environment_type: Type of environment (e.g., dev, qa, performance, release, preprod)
- start_date: Date in YYYY-MM-DD format (use {current_date} for "today")
- start_time: Time in HH:MM:SS AM/PM format
- duration_hours: Number of hours (can be decimal like 1.5)
- purpose: Please describe briefly what this environment will be used for
- tools: List of tools/services needed
- user_name: Name of person requesting the booking
- clarification_needed: true if missing required info, false if complete
- clarification_question: Question to ask if clarification_needed is true

EXAMPLES:
User: "book a QA environment for today at 2pm for 1 hour"
Response: {{"environment_type": "QA", "start_date": "{current_date}", "start_time": "02:00:00 PM", "duration_hours": 1, "purpose": null, "tools": ["none"], "user_name": null, "clarification_needed": true, "clarification_question": "Who should I book this environment for?"}}

User: "I need a performance environment with Jenkins and Grafana today at 3pm for 2 hours, my name is John"
Response: {{"environment_type": "Performance", "start_date": "{current_date}", "start_time": "03:00:00 PM", "duration_hours": 2, "purpose": "Performance Testing", "tools": ["Jenkins", "Grafana"], "user_name": "John", "clarification_needed": false, "clarification_question": null}}

Return ONLY the JSON object, no other text. Use this schema: {parsing_schema}

User request: '{user_request}'"""

SUCCESS_EXAMPLE = {
    "environment_type": "QA",
    "start_date": "2025-01-20",
    "start_time": "02:00:00 PM",
    "duration_hours": 1,
    "purpose": "Performance Testing",
    "tools": ["Postman", "MongoDB"],
    "user_name": "shashi",
    "clarification_needed": False,
    "clarification_question": None
}

MISSING_EXAMPLE = {
    "environment_type": None,
    "start_date": None,
    "start_time": "10:00:00 AM",
    "duration_hours": None,
    "purpose": "Performance Testing",
    "tools": ["neoload"],
    "user_name": None,
    "clarification_needed": True,
    "clarification_question": "Could you confirm the environment type (e.g., QA, Dev, Performance) and date for this booking?"
}

DEFAULT_AGENT_STATE = {
    'user_input': "",
    'llm_response': "",
    'messages': [],
    'parsed_request': {
        'environment_type': None,
        'start_date': None,
        'start_time': None,
        'duration_hours': None,
        'purpose': None,
        'tools': [],
        'user_name': None
    },
    'clarification_needed': False,
    'clarification_question': None,
    'user_name_for_booking': None,

    'matching_environments': [],
    'available_environments': [],
    'alternative_environments': [],
    'selected_environment': None,
    'user_confirmation': None,
    'booking_result': False,

    'error_message': None
}

ENVIRONMENT_TEMPLATE = "\n".join([
    "Please politely inform the user with a friendly tone about the available environments.",
    "Here are the available environments: {environments}"
])