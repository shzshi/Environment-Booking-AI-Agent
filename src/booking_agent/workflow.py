# src/booking_agent/workflow.py
"""Workflow using LangGraph for environment booking tool."""

from langgraph.graph import StateGraph, END
from booking_agent.schemas import AgentState
from booking_agent.nodes import *
from booking_agent.conditions import *
from helper import initialize_llm
from config import TEMPERATURE
# (
#     parse_request, ask_clarification, handle_error,
#     find_matching_environments, find_booking_options, 
#     search_alternative_environments, confirm_booking,
#     select_environment, inform_user,
#     is_clear_request, is_confirmed
# )

# Define constants for node names
PARSE_REQUEST = "parse_request_node"
ASK_CLARIFICATION = "ask_clarification_node"
HANDLE_ERROR = "handle_error_node"
FIND_MATCHING_ENVIRONMENT = "find_matching_environments_node"
FIND_BOOKING_OPTIONS = "find_booking_options_node"
SEARCH_ALTERNATIVE_ENVIRONMENTS = "search_alternative_environments_node"
CHOOSE_ALTERNATIVE_ENVIRONMENTS = "choose_alternative_environments_node"
CONFIRM_BOOKING = "confirm_booking_node"
INFORM_USER = "inform_user_node"
CHECK_TIME_CONFLICT = "check_time_conflict_node"

def create_workflow():

    #########################################################################
    # INTIALIZE WORKFLOW
    #########################################################################
    workflow = StateGraph(AgentState)
    llm = initialize_llm(name="groq", temp=TEMPERATURE)
    # workflow.set_state(AgentState.INITIAL)
    # workflow.set_transition_logger(lambda from_node, to_node: print(f"Transition: {from_node} -> {to_node}"))

    # --- nodes ---
    workflow.add_node(PARSE_REQUEST, lambda state: parse_request(state, llm))
    workflow.add_node(ASK_CLARIFICATION, ask_clarification)
    workflow.add_node(HANDLE_ERROR, handle_error)
    workflow.add_node(FIND_MATCHING_ENVIRONMENT, lambda state: find_matching_environments(state, llm))
    workflow.add_node(FIND_BOOKING_OPTIONS, find_booking_options)
    workflow.add_node(SEARCH_ALTERNATIVE_ENVIRONMENTS, search_alternative_environments)
    workflow.add_node(CHOOSE_ALTERNATIVE_ENVIRONMENTS, select_environment)
    workflow.add_node(CONFIRM_BOOKING, confirm_booking)
    workflow.add_node(INFORM_USER, inform_user)

    # --- edges ---
    workflow.add_conditional_edges(
        PARSE_REQUEST,
        is_clear_request,
        {
            "ask_clarification": ASK_CLARIFICATION,
            "find_matching_environments": FIND_MATCHING_ENVIRONMENT,
            "handle_error": HANDLE_ERROR,
        },
    )

    workflow.add_conditional_edges(
        FIND_MATCHING_ENVIRONMENT,
        lambda state: bool(state.get("matching_environments")),
        {
            True: FIND_BOOKING_OPTIONS,
            False: SEARCH_ALTERNATIVE_ENVIRONMENTS,
        },
    )

    workflow.add_conditional_edges(
        FIND_BOOKING_OPTIONS,
        lambda state: len(state.get("available_environments", [])) > 0,
        {
            True: CHOOSE_ALTERNATIVE_ENVIRONMENTS,
            False: HANDLE_ERROR,
        },
    )

    workflow.add_conditional_edges(
        SEARCH_ALTERNATIVE_ENVIRONMENTS,
        lambda state: len(state.get("alternative_environments", [])) > 0,
        {
            True: CHOOSE_ALTERNATIVE_ENVIRONMENTS,
            False: ASK_CLARIFICATION,
        },
    )

    workflow.add_edge(CHOOSE_ALTERNATIVE_ENVIRONMENTS, CONFIRM_BOOKING)

    workflow.add_conditional_edges(
        CONFIRM_BOOKING,
        lambda state: state.get("booking_result", False),
        {
            True: INFORM_USER,
            False: HANDLE_ERROR,
        },
    )

    workflow.add_edge(INFORM_USER, END)
    workflow.add_edge(ASK_CLARIFICATION, END)

    workflow.add_conditional_edges(
        HANDLE_ERROR,
        lambda state: state.get("clarification_needed", False),
        {
            True: ASK_CLARIFICATION,
            False: END,
        },
    )

    # --- entry & compile ---
    workflow.set_entry_point(PARSE_REQUEST)
    return workflow.compile()