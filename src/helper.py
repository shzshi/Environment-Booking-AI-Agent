
# src/helper.py
import json
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser

from typing import Dict

from config import *
from booking_agent.schemas import *
from booking_agent.prompt_config import *
from mock_apis.booking_services import *
from mock_apis.environment_services import *

REQUIRED_FIELDS = [
    "start_date", "start_time", "duration_hours", 
    "tools", "purpose"
]

def initialize_llm(name: str, temp: float=0.0):
    """
    Initialize the LLM with tools. we can choose from different types of LLMs.
    """
    if name.lower() == "ollama":
        llm = ChatOllama(model_name=OLLAMA_MODEL_NAME,
                          ollama_api_key=OLLAMA_API_KEY,
                          temperature=temp)
        logger.info(f">>>> Load Ollama: {OLLAMA_MODEL_NAME} model correctly.")
    
    elif name.lower() == "gemini":
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME,  # Explicitly pass the model
                                      google_api_key=GEMINI_API_KEY,
                                      temperature=temp)
        logger.info(f">>>> Load Gemini: {GEMINI_MODEL_NAME} model correctly.")

    elif name.lower() == "groq":
        llm = ChatGroq(model_name=GROQ_MODEL_NAME,
                        groq_api_key=GROQ_API_KEY,
                        temperature=temp)
        logger.info(f">>>> Load Groq: {GROQ_MODEL_NAME} model correctly.")

    else:
        raise ValueError(f"Unsupported LLM: {name}")
    
    # llm.bind_tools([
    #     save_bookings_tool,
    #     check_time_conflict_tool,
    #     # book_environment_tool,
    #     find_matching_environments_tool,
    #     # find_similar_environments_tool,
    #     # find_environments_by_equipments_tool,
    # ])

    return llm

def apply_request_prompt(parsing_schema: PydanticOutputParser) -> PromptTemplate: 
    """
    Apply the prompt template to the LLM. Variables are defined in prompt_config.py
    """
    prompt_template = PromptTemplate(
        input_variables = ["user_request", "current_date", "current_time"],
        template = REQUEST_TEMPLATE,
        partial_variables = {
            "parsing_schema": parsing_schema.get_format_instructions(),
            "successful_example": json.dumps(SUCCESS_EXAMPLE, indent=2),
            "missing_example": json.dumps(MISSING_EXAMPLE, indent=2)
        })
    return prompt_template

def apply_environments_prompt(environments: List[Dict]) -> PromptTemplate:
    """
    Generate a user-friendly message listing available environments.
    """
    return PromptTemplate(
        input_variables = ["environments"],
        template = ENVIRONMENT_TEMPLATE
    )

# def matching_environment_msg(environments: List[Dict]):

#     environment_messages = [
#         f"Environment '{environment['type']}' with a capacity of {environment['capacity']} people "
#         f"and equipped with {', '.join(environment['equipments'])}."
#         for environment in environments
#     ]
#     return "Here are the available environments:\n" + "\n".join(environment_messages)

def message_to_dict(message):
    """
    Convert message objects to serializable dictionaries for Flask session
    """
    return {
        'type': message.type,
        'content': message.content,
        'additional_kwargs': message.additional_kwargs
    }

def dict_to_message(data):
    """
    Convert dictionaries comes from Flask session to message objects for LLM response
    """
    if data['type'] == 'human':
        return HumanMessage(**data)
    return SystemMessage(**data)

def get_missing_fields(parsed_request: dict) -> list:
    """
    Get a list of missing fields from the parsed request.
    """
    
    return [
        field for field in REQUIRED_FIELDS
        if not parsed_request.get(field)
        # or (parsed_request[field] == "nothing")
        or (field == "duration_hours" and parsed_request[field] <= 0)
    ]
def load_clarification_msgs(filepath:str = MSG_JSON_FILE) -> Dict:
    """
    Load clarification messages from a JSON file.
    """
    with open(filepath, "r") as file:
        return json.load(file)



# def format_available_times_msg(available_times: dict) -> str:
#     """
#     Generate a user-friendly message listing available times for matching environments.
#     """
#     if not available_times:
#         return "No available times found for the matching environments."

#     messages = [
#         f"environment '{environment}' NOT available at the following times: {', '.join(times)}"
#         for environment, times in available_times.items()
#     ]
#     return "Here are the available times for the matching environments:\n" + "\n".join(messages)

#### Deprecated: Let LLM handle the clarifications ####
# def get_clarification_question(state: AgentState) -> str:
#     if not state["parsed_request"].get("start_time"):
#         return "What time should I book the environment for?"
#     if not state["parsed_request"].get("duration_hours"):
#         return "How many hours will the meeting last?"
#     if not state["parsed_request"].get("capacity"):
#         return "What is the capacity of the environment?"
#     if not state["parsed_request"].get("equipments"):
#         return "What equipment do you need in the environment?"
#     if not state["user_name_for_booking"]:
#         return "Could you please provide your name for the booking?"
#     return "Could you please clarify your request?"

