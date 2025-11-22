# src/mock_apis/environment_services.py
import json
from pathlib import Path
from typing import List, Dict
from config import ENVIRONMENTS_FILE
from booking_agent.schemas import Environment
from helper import *
from config import logger
# from langchain_core.tools import tool

def check_environment_availability_tool(environment: Dict, tools: List[str]) -> bool:
    """
    Check if the environment has all the specified tool (case-insensitive, partial matching).
    """
    for eq in tools:
        if eq.lower() == "nothing": 
            continue
        
        # Case-insensitive partial matching
        eq_lower = eq.lower()
        environment_tools_lower = [e.lower() for e in environment['tools']]
        
        # Check for exact match or partial match
        found = False
        for environment_eq in environment_tools_lower:
            # Check if the requested tool is contained in the environment tool
            if eq_lower in environment_eq:
                found = True
                break
            # Check if environment tool is contained in the requested tool
            if environment_eq in eq_lower:
                found = True
                break
            # Check for word-based matching (e.g., "laptop" matches "laptop connections")
            eq_words = eq_lower.split()
            environment_eq_words = environment_eq.split()
            
            # Check for direct word match
            if any(eq_word in environment_eq_words for eq_word in eq_words):
                found = True
                break
            
            # Check for singular/plural variations
            for eq_word in eq_words:
                # Try singular version (remove 's' from end)
                if eq_word.endswith('s') and len(eq_word) > 1:
                    singular = eq_word[:-1]
                    if singular in environment_eq_words:
                        found = True
                        break
                # Try plural version (add 's' to end)
                plural = eq_word + 's'
                if plural in environment_eq_words:
                    found = True
                    break
            
            if found:
                break
        
        if not found:
            return False
    return True

#@tool("load_environments", description="Load existing environment options from external file. ")
def load_environments(filepath: Path = ENVIRONMENTS_FILE) -> List[Dict]:
    """
    Load existing environment options from external file. 
    """
    existing_data: List[Dict] = []
    try:
        with open(filepath, "r") as f:
            existing_data = json.load(f)
        logger.info(f"Loaded {len(existing_data)} environments from {filepath}")
    except json.JSONDecodeError as e:
        logger.error(f"Warning: Could not decode existing JSON in {filepath}: {e}. Starting fresh.")
        existing_data = []
    except FileNotFoundError:
        logger.error(f"Warning: environments file {filepath} not found. Starting fresh.")
        existing_data = []
    return existing_data


#@tool("find_matching_environments", description="Find environments that match the required purpose and tool.")
def find_matching_environments_tool(existing_environments: List[Dict], purpose: str, tools: List[str]) -> List[Dict]:
    """
    Find environments that match the required purpose and tool.
    """
    matching_environments = []
    for environment in existing_environments:
        if environment['purpose'].lower() == purpose.lower() and check_environment_availability_tool(environment, tools):
            matching_environments.append(environment)
    return matching_environments

# @tool("find_similar_environments", description="Find environments with similar tool and purpose.")
# def find_similar_environments_tool(tool_input: dict) -> List[Dict]:
#     purpose = tool_input.get("purpose", "")
#     tools = tool_input.get("tools", [])
#     top_n = tool_input.get("top_n", 3)

#     environments = load_environments()
#     scored_environments = []
#     for environment in environments:
#         if environment["purpose"].lower() == purpose.lower():
#             overlap = len(set(environment["tools"]) & set(tools))
#             scored_environments.append((overlap, environment))

#     scored_environments.sort(reverse=True, key=lambda x: x[0])
#     return [environment for overlap, environment in scored_environments if overlap > 0][:top_n]

@tool("find_similar_environments", description="Find environments with similar tool and purpose.")
def find_similar_environments_tool(purpose: str, tools: List[str], top_n: int = 3) -> List[Dict]:

    environments = load_environments()
    scored_environments = []

    for environment in environments:
        if environment["purpose"].lower() == purpose.lower():
            logger.info(f" {environment['purpose']} compare {purpose}")
            overlap = len(set(environment["tools"]) & set(tools))
            logger.info(f" overlap {overlap}")
            scored_environments.append((overlap, environment))

    scored_environments.sort(reverse=True, key=lambda x: x[0])
    return [environment for overlap, environment in scored_environments if overlap > 0][:top_n]

@tool("find_environments_by_tools", description="Find environments that have all the specified tool.")
def find_environments_by_tools_tool(tools: List[str]) -> List[Environment]:
    environments = load_environments()
    matching_environments = []
    for environment in environments:
        if all(feature in environment.tools for feature in tools):
            matching_environments.append(environment)
    return matching_environments

@tool("find_environments_by_purpose", description="Find environments that have a purpose greater than or equal to the specified value.")
def find_environments_by_purpose_tool(purpose: str) -> List[Environment]:
    environments = load_environments()
    matching_environments = []
    for environment in environments:
        if environment.purpose.lower() == purpose.lower():
            matching_environments.append(environment)
    return matching_environments
