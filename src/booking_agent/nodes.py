# src/booking_agent/nodes.py

"""Individual nodes and conditions for the workflow of booking meeting environments."""
import random
from datetime import datetime
from langgraph.graph import END
from langchain.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime, timedelta

from helper import *
from config import logger
from mock_apis.booking_services import *
from mock_apis.environment_services import *
from booking_agent.schemas import AgentState, BookingRequest

##==============================================================================
# NODE FUNCTIONS
##==============================================================================
# NODE [01]. Parsing user requests Node
def parse_request(state: AgentState, llm) -> AgentState:
    logger.info(" ------------------ NODE: PARSE REQUEST ------------------ ")

    ######################## (1.) Initialization ######################
    current_date = datetime.now().strftime('%Y-%m-%d')    # e.g, 2025-05-12
    current_time = datetime.now().strftime('%I:%M:%S %p') # e.g, 02:45:30 PM
    logger.info(" >>>>> CURRENT DATE: %s", current_date)
    logger.info(" >>>>> CURRENT TIME: %s", current_time)
    # Initialize parser used for user request parsing
    parser = PydanticOutputParser(pydantic_object=BookingRequest)
    # Apply template to the inputrequest to inject the predefined template prompt
    prompt_template = apply_request_prompt(parser)
    # Initialize LLM
    try:
        # llm = initialize_llm(name="groq")
        # Create chain
        chain = prompt_template | llm | parser
        ############## (2.) Update conversation history ##################
        # logger.info(" >>>>> USER INPUT : %s", state['user_input'])
        state["messages"].append(HumanMessage(content=state['user_input']))
        # Build full request context from conversation history ####
        conversation_context = "\n".join(
            f"{'USER' if isinstance(msg, HumanMessage) else 'AGENT'}: {msg.content}"
            for msg in state["messages"]
        )
        logger.info("\n>>>>> CONVERSION CONTEXT: %s", conversation_context)

        ######################## (3.) Invoke chain ########################
        try:
            parsed_data = chain.invoke({"user_request": conversation_context,
                                        "current_date": current_date,
                                        "current_time": current_time})
            
            logger.info("\n >>>>>>> PARSED REQUEST: %s", parsed_data.model_dump())
        except Exception as parse_error:
            logger.error(f"Error during LLM parsing: {str(parse_error)}")
            logger.error(f"User request: {conversation_context}")
            logger.error(f"Current date: {current_date}, Current time: {current_time}")
            # Set a default parsed request to avoid crashes
            parsed_data = BookingRequest(
                start_date=None,
                start_time=None,
                duration_hours=None,
                purpose=None,
                tools=[],
                user_name=None,
                clarification_needed=True,
                clarification_question="I'm having trouble processing your request. Could you please provide the booking details again?"
            )
        state.update({
            "parsed_request": parsed_data.model_dump(),
            "user_name_for_booking": parsed_data.user_name,
            })
    except Exception as e:
        state["error_message"] = f"Failed to parse request: {str(e)}"   
        return state
    
    return state

# NODE [02]. Ask Clarification Node
def ask_clarification(state: AgentState) -> AgentState:
    """
    Add Clarification question to messages.
    """
    logger.info(" ------------------ NODE: ASK CLARIFICATION ------------------ ")

    # Try to get clarification question from parsed request
    clarification_msg = state['parsed_request'].get('clarification_question')
    
    # If no clarification question provided, generate one based on missing fields
    if not clarification_msg:
        missed_fields = get_missing_fields(state["parsed_request"])
        if missed_fields:
            # Create a simple clarification question based on missing fields
            if 'purpose' in missed_fields:
                clarification_msg = "What is the purpose of the booking?"
            elif 'tools' in missed_fields:
                clarification_msg = "What tools or services are required in the environment?"
            elif 'user_name' in missed_fields:
                clarification_msg = "What's your name for the booking?"
            else:
                clarification_msg = f"Could you please provide the {', '.join(missed_fields)} for your booking?"
        else:
            clarification_msg = "Could you please provide more details for your booking?"
    
    state["clarification_question"] = clarification_msg
    logger.info(f">>> CLARIFICATION QUESTION: {state['clarification_question']}")
    state["messages"].append(SystemMessage(content=state["clarification_question"]))

    return state

# NODE [03]. Searching for environments that matches the purpose and tool
def find_matching_environments(state: AgentState, llm) -> AgentState:
    """
    Find all environments that match the user's requirements (purpose, tool).
    """
    logger.info(" ------------------ NODE: GET MATCHING ENVIRONMENTS ------------------ ")
 
    try:
        existing_environments = load_environments()
        purpose = state["parsed_request"]["purpose"]
        tools = state["parsed_request"].get("tools", [])

        logger.info("\n>>>>> tools values: %s", tools)
        logger.info("\n>>>>> purpose values: %s", purpose)
        
        matching_environments = find_matching_environments_tool(
            existing_environments,
            purpose=purpose,
            tools=tools
        )

        logger.info("\n>>>>> matching environments values: %s", matching_environments)
        
        state["matching_environments"] = matching_environments
        # Ask LLM to make this in summerized response
        conversation_context = "\n".join(
            f"{'USER' if isinstance(msg, HumanMessage) else 'AGENT'}: {msg.content}"
            for msg in state["messages"]
        )
        environments_prompt = apply_environments_prompt(matching_environments)
        chain = environments_prompt | llm 
        logger.info("\n>>>>> CONVERSION CONTEXT: %s", conversation_context)
        # Invoke chain 
        matching_environments_conclusion = chain.invoke({"environments": matching_environments}).content
        logger.info(" >>>>>>> MATCHING ENVIRONMENTS: %s", matching_environments_conclusion)

        state["messages"].append(SystemMessage(content=matching_environments_conclusion))
        logger.info(" >>>>>>> MATCHING ENVIRONMENTS: %s", state["messages"])
        return state

    except Exception as e:
        logger.error(f"Error finding matching environments: {str(e)}")
        state["matching_environments"] = []
        state["error_message"] = f"Failed to find matching environments: {str(e)}"
        return state

# NODE [04]. Define the availability of the matching environments
def find_booking_options(state: AgentState) -> AgentState:
    logger.info(" ------------------ NODE: GET AVAILABLE ENVIRONMENTS ------------------ ")
    """
    For each matching environment, check if it's available at the requested time.
    """
    logger.info(" ------------------ NODE: GET AVAILABLE ENVIRONMENTS ------------------ ")
    
    available_environments = []
    unavailable_environments = []
    
    logger.info(" >>>>>>> MATCHING ENVIRONMENTS: %s", state.get("matching_environments", []))
    logger.info(" >>>>>>> PARSED REQUEST: %s", state["parsed_request"])

    date_str = state["parsed_request"]["start_date"]
    start_time_str = state["parsed_request"]["start_time"]
    
    start_time = combine_date_time(date_str, start_time_str)

    logger.info("booking['start_time'] value: %s (%s)", start_time, type(start_time))


    try:
        existing_bookings = load_bookings()
        # for environment in state["matching_environments"]:
        #     # Check if environment is available in the given time slot
        #     logger.info(" >>>>>>> CHECKING environment AVAILABILITY: %s", environment.id)
        #     logger.info(" >>>>>>> CHECKING environment AVAILABILITY: %s", state["parsed_request"]["start_time"])
        #     if check_time_conflict_tool(
        #         existing_bookings=existing_bookings, environment_id=environment.id,
        #         start_time=state["parsed_request"]["start_time"],
        #         duration_hours=state["parsed_request"]["duration_hours"]
        #     ):
        #         unavailable_environments.append(environment)
        #     else:
        #         available_environments.append(environment)

        for environment in state.get("matching_environments", []):
            environment_id = environment["id"]  # <-- use dictionary key instead of .id
            conflict = check_time_conflict_tool(
                existing_bookings=existing_bookings,
                environment_id=environment_id,
                start_time=start_time,
                duration_hours=state["parsed_request"]["duration_hours"]
            )
            if conflict:
                unavailable_environments.append(environment)
            else:
                available_environments.append(environment)


        logger.info(" >>>>>>> AVAILABLE ENVIRONMENTS: %s",
                   "NO AVAILABLE ENVIRONMENTS" if not available_environments else available_environments)
        
        state["available_environments"] = available_environments
        state["unavailable_environments"] = unavailable_environments
        
    except Exception as e:
        logger.error(f"Error checking environment availability: {str(e)}")
        state["error_message"] = f"Failed to check environment availability: {str(e)}"
        state["available_environments"] = []
        state["unavailable_environments"] = []

    logger.info(" >>>>>>> UNAVAILABLE ENVIRONMENTS: %s", state.get("unavailable_environments", "NO UNAVAILABLE ENVIRONMENTS"))
    # logger.info(" >>>>>>> AVAILABLE environments:", state.get("available_environments", "NO FREE AVAILABLE environments"))
    logger.info(" >>>>>>> AVAILABLE ENVIRONMENTS: %s", state.get("available_environments", "NO FREE AVAILABLE ENVIRONMENTS"))

    return state


# NODE [03]. Handle Error Node
def handle_error(state: AgentState) -> AgentState:
    """
    Handle errors and provide appropriate feedback to the user.
    """
    logger.info(" ------------------ NODE: HANDLE ERROR ------------------ ")
    msgs = load_clarification_msgs()

    # Customize error message based on state
    if not state.get("matching_environments", []):
        error_msg = msgs['no_matching_environments']
    elif not state.get("available_environments", []):
        error_msg = msgs['no_available_times']
    elif state.get("booking_result") is False:
        error_msg = msgs['booking_error']
    else:
        error_msg = state.get("error_message", "Sorry! we are out of service now.")

    logger.info(" >>>>>>> ERROR MESSAGE: %s", error_msg)
    state["messages"].append(SystemMessage(content=error_msg))
    state["error_message"] = error_msg

    return state

def select_environment(state: AgentState) -> AgentState:
    """
    Select a environment from the available alternatives.
    """
    logger.info(" ------------------ NODE: SELECT environment ------------------ ")

    available_environments = state.get("available_environments") or state.get("alternative_environments") or []

    logger.info(" >>>>>>> ALTERNATIVE ENVIRONMENTS: %s", available_environments[0])
    
    try:
        # available_environments = state.get("available_environments") or state.get("alternative_environments") or []
        if available_environments:
            selected = available_environments[0]
            state["selected_environment"] = selected
            state["llm_response"] = (
                f"I've selected {selected['name']} for you which has:\n"
                f"- purpose: {selected['purpose']} people\n"
                f"- Tool: {', '.join(selected['tools'])}"
            )
        else:
            state["selected_environment"] = None
            state["llm_response"] = "No suitable environment found to select."
            
    except Exception as e:
        logger.error(f"Error selecting environment: {str(e)}")
        state["error_message"] = f"Failed to select environment: {str(e)}"
        state["selected_environment"] = None
        state["llm_response"] = "Sorry, I encountered an error while selecting a environment."
    
    state["messages"].append(SystemMessage(content=state["llm_response"]))
    return state

def suggest_alternative_times(state: AgentState) -> AgentState:
    """
    For environments that match requirements but are not available at the requested time,
    the agent should find and suggest their next available time slots.
    """
    logger.info(" ------------------ NODE: SEARCH ALTERNATIVE TIMES ------------------ ")
    
    try:
        if not state.get("selected_environment"):
            raise ValueError("No environment selected to find alternatives for")
            
        alternative_times = {}
        for environment in state.get("matching_environments", []):
            times = check_time_conflict_tool(
                environment_id=environment.id,
                start_time=state["parsed_request"]["start_time"],
                duration_hours=state["parsed_request"]["duration_hours"]
            )
            if times:
                alternative_times[environment.id] = times

        if alternative_times:
            state["llm_response"] = format_available_times_msg(alternative_times)
        else:
            state["llm_response"] = "Sorry, I couldn't find any alternative times for the environments."
            state["error_message"] = "No alternative times available"
            
    except Exception as e:
        logger.error(f"Error finding alternative times: {str(e)}")
        state["error_message"] = f"Failed to find alternative times: {str(e)}"
        state["llm_response"] = "Sorry, I encountered an error while searching for alternative times."
    
    state["messages"].append(SystemMessage(content=state["llm_response"]))
    return state

def confirm_booking(state: AgentState) -> AgentState:
    """
    Complete the booking process and save the booking record.
    """
    logger.info(" ------------------ NODE: CONFIRM BOOKING ------------------ ")
    
    try:
        if not state.get("selected_environment"):
            raise ValueError("No environment selected for booking")
            
        booking_data = state["parsed_request"]
        environment = state["selected_environment"]
        date_str = booking_data["start_date"]
        start_time_str = booking_data["start_time"]

        start_time = combine_date_time(date_str, start_time_str)
        
        # if only duration provided, compute end time
        duration_hours = booking_data["duration_hours"]
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(hours=duration_hours)
        end_time = end_dt.isoformat()

        logger.info(" >>>>>>> start date and time: %s", start_time)
        logger.info(" >>>>>>> end date and time: %s", end_time)

        # end_time = datetime.fromisoformat(start_time) + \
        #           timedelta(hours=booking_data["duration_hours"])
        
        # Create the booking using the tool
        # booking_result = book_environment_tool(
        #     environment_id=int(environment["id"]),
        #     start_time=booking_data["start_time"],
        #     end_time=end_time.isoformat(),
        #     user_name=booking_data["user_name"]
        # )

        booking_input = {
            "environment_id": int(environment["id"]),
            "start_time": start_time,
            "end_time": end_time,
            "user_name": booking_data["user_name"],
        }

        booking_result = book_environment_tool.invoke(booking_input)

        logger.info(" booking results : %s", booking_result)
        
        state["booking_result"] = True if booking_result else False

        environment = state.get("selected_environment", {})
        environment_name = environment.get("name", "your environment")

        if booking_result:
            state["user_booking_confirmation"] = "yes"
            state["llm_response"] = f"Successfully booked {environment_name} for you!"
        else:
            raise ValueError("Booking creation failed")
            
    except Exception as e:
        logger.error(f"Booking failed: {str(e)}")
        state["booking_result"] = False
        state["error_message"] = f"Failed to complete the booking: {str(e)}"
        state["user_booking_confirmation"] = "no"
    
    return state

def search_alternative_environments(state: AgentState) -> AgentState:
    """
    Search for alternative environments when no exact matches are found.
    Uses similarity matching to find environments with close specifications.
    """
    logger.info(" ------------------ NODE: SEARCH ALTERNATIVE ENVIRONMENTS ------------------ ")
    
    try:
        purpose = state["parsed_request"]["purpose"]
        tools = state["parsed_request"].get("tools", [])
        
        logger.info(f" >>>>>>> PURPOSE: {purpose}")
        logger.info(f" >>>>>>> TOOLS: {tools}")

        logger.info(f"Type of find_similar_environments_tool: {type(find_similar_environments_tool)}")

        # Find similar environments using the similarity tool
        alternative_environments = find_similar_environments_tool.invoke({
            "purpose": purpose, 
            "tools": tools
        })

        logger.info(f" >>>>>>> ALTERNATIVE ENVIRONMENTS: {alternative_environments}")
        
        state["alternative_environments"] = alternative_environments if alternative_environments else []
        
        if alternative_environments:
            logger.info(f" >>>>>>> FOUND {len(alternative_environments)} ALTERNATIVE ENVIRONMENTS")
            state["llm_response"] = "I found some alternative environments that might work for you: \n" + \
                "\n".join([f"- {environment.name}: purpose {environment.purpose}, Tool: {', '.join(environment.tools)}"
                          for environment in alternative_environments])
        else:
            logger.info(" >>>>>>> NO ALTERNATIVE ENVIRONMENTS FOUND")
            state["llm_response"] = "I couldn't find any alternative environments matching your requirements."
            
    except Exception as e:
        logger.error(f"Error finding alternative environments: {str(e)}")
        state["error_message"] = f"Failed to find alternative environments: {str(e)}"
        state["alternative_environments"] = []
        state["llm_response"] = "Sorry, I encountered an error while searching for alternative environments."
    
    state["messages"].append(SystemMessage(content=state["llm_response"]))
    return state

def inform_user(state: AgentState) -> AgentState:
    """
    Inform the user about the booking status and provide relevant information.
    """
    logger.info(" ------------------ NODE: INFORM USER ------------------ ")
    
    try:
        if state.get("booking_result"):
            booking = state.get("parsed_request", {})
            environment = state.get("selected_environment", {})
            
            # Handle tool list formatting
            tools = environment.get("tools", [])
            tool_str = ", ".join(tools) if tools else "No special tool"
            
            state["llm_response"] = (
                f"Great! I've successfully booked {environment.get('name', 'the environment')} for you:\n"
                f"- Date: {booking.get('start_date', 'N/A')}\n"
                f"- Time: {booking.get('start_time', 'N/A')} "
                f"(for {booking.get('duration_hours', 0)} hours)\n"
                f"- Booked under: {booking.get('user_name', 'N/A')}\n"
                f"- Environment purpose: {environment.get('purpose', 'N/A')} people\n"
                f"- Tool: {tool_str}\n\n"
                f"Your booking has been confirmed and saved. You'll receive a notification "
                f"with the booking details."
            )
        else:
            state["llm_response"] = (
                "I'm sorry, but the booking couldn't be completed. "
                "Would you like to:\n"
                "- Try booking a different environment\n"
                "- Check alternative time slots\n"
                "- Start a new search"
            )
            state["clarification_needed"] = True
            
    except Exception as e:
        logger.error(f"Error formatting user response: {str(e)}")
        state["error_message"] = f"Failed to format response: {str(e)}"
        state["llm_response"] = "Sorry, I encountered an error while preparing the booking confirmation."
    
    state["messages"].append(SystemMessage(content=state["llm_response"]))
    return state


def normalize_time(time_str: str) -> str:
    """
    Convert time string into ISO datetime with dummy date (1970-01-01).
    """
    try:
        t = datetime.strptime(time_str, "%I:%M:%S %p").time()
    except ValueError:
        t = datetime.strptime(time_str, "%H:%M:%S").time()

    dt = datetime.combine(datetime(1970, 1, 1).date(), t)
    return dt.isoformat()


def combine_date_time(date_str: str, time_str: str) -> str:
    """
    Combine a date string (YYYY-MM-DD) and time string (12h or 24h)
    into a full ISO datetime string (YYYY-MM-DDTHH:MM:SS).
    """
    # Normalize time string
    try:
        t = datetime.strptime(time_str, "%I:%M:%S %p").time()  # "05:00:00 PM"
    except ValueError:
        try:
            t = datetime.strptime(time_str, "%I:%M %p").time()  # "5:00 PM"
        except ValueError:
            try:
                t = datetime.strptime(time_str, "%H:%M:%S").time()  # "17:00:00"
            except ValueError:
                t = datetime.strptime(time_str, "%H:%M").time()  # "17:00"

    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return datetime.combine(d, t).isoformat()
