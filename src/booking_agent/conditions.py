# src/booking_agent/conditions.py

from mock_apis.booking_services import *
from mock_apis.environment_services import *
from booking_agent.schemas import AgentState
from config import logger
import random

from helper import get_missing_fields

########################################################################
# CONDITIONS:
########################################################################
# CONDITION [1]. Check Valid Request Condition
def is_clear_request(state: AgentState) -> str:
    """
    Check if the user request is clear (NO Nulls in parsed request) and valid (no system errors).
    """
    logger.info(" ------------------ CONDITION: Check Valid and Clear Request ------------------ ")
    missed_fields = get_missing_fields(state["parsed_request"])
    
    # Check if clarification is explicitly needed from the parsed request
    clarification_needed = state["parsed_request"].get("clarification_needed", False)

    if len(missed_fields) > 0 or clarification_needed:
        logger.error(f"Missing mandatory fields in parsed_data: {missed_fields}")
        logger.info(f"Clarification needed: {clarification_needed}")
        return "ask_clarification"

    elif state.get("error_message"):
        return "handle_error"

    else:
        return "find_matching_environments"


# CONDITION [2]. Check if user confirm booking
def is_confirmed(state: AgentState) -> bool:
    logger.info(" --->>>> CONDITION: Check if user confirm booking <<<<--- ")
    if state["user_booking_confirmation"].lower() in ["yes", "y"]:
        return True
    else:
        state["clarification_needed"] = True
        state["clarification_question"] = "Booking Not Confimed. Do you want to book another room?"
        return False

def should_suggest_alternatives(state: AgentState) -> bool:
    
    return len(state.get("available_rooms", [])) == 0
