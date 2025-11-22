# src/mock_apis/booking_services.py
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict

from langchain_core.tools import tool

from config import BOOKINGS_FILE, DELAY, logger
from booking_agent.schemas import Booking


# @tool("load_bookings", description="Load existing bookings from external file.")
def load_bookings(
        filepath: Path = BOOKINGS_FILE
    ) -> Dict[str, List[Dict[str, Union[str, datetime]]]]:
    """Load existing bookings from external file."""
    existing_data: Dict[str, List[Dict[str, Union[str, datetime]]]] = {}
    try:
        with open(filepath, "r") as f:
            existing_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode existing JSON in {filepath}. Starting fresh.")
        existing_data = {}
    return existing_data


# @tool("save_bookings", description="Save bookings to the database.")
def save_bookings_tool(
        environment_id: Union[int, str], 
        booking: Dict, file_path: Path = BOOKINGS_FILE
    ):
    """Save bookings to the database."""
    bookings = load_bookings()
    environment_id = str(environment_id)
    environment_id_bookings = bookings.get(environment_id, [])
    print(f"Current bookings for environment_id {environment_id}: {environment_id_bookings}")
    environment_id_bookings.append(booking)
    bookings[environment_id] = environment_id_bookings

    with open(file_path, "w") as f:
        json.dump(bookings, f, indent=4)

# @tool("check_time_conflict", description="Check if a environment_id has a time conflict for the requested time.")
def check_time_conflict_tool(
        existing_bookings: Dict[str, List[Dict[str, str]]],
        environment_id: int,
        start_time: Union[str, datetime],
        end_time: Optional[Union[str, datetime]] = None,
        duration_hours: Optional[float] = None,
    ) -> bool:
    """Check if a environment_id has a time conflict for the requested time."""

    logger.info("existing_bookings keys: %s", list(existing_bookings.keys()))
    logger.info("Requested environment_id: %s", environment_id)

    # Normalize times
    if isinstance(start_time, str):
        try:
            start_time = datetime.fromisoformat(start_time)
        except ValueError:
            start_time = datetime.strptime(start_time, "%H:%M:%S")  # fallback
    if end_time is None and duration_hours:
        end_time = start_time + timedelta(hours=duration_hours)
    elif isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    logger.info("Normalized start_time: %s", start_time)
    logger.info("Normalized end_time: %s", end_time)

    # environment_id IDs in JSON are stored as strings
    environment_id_bookings = existing_bookings.get(str(environment_id), [])
    logger.info("environment_id_bookings for environment_id %s: %s", environment_id, environment_id_bookings)

    for booking in environment_id_bookings:
        booking_start = datetime.fromisoformat(booking["start_time"])
        booking_end = datetime.fromisoformat(booking["end_time"]) + DELAY

        if start_time < booking_end and end_time > booking_start:
            logger.info("Conflict found with booking %s - %s", booking_start, booking_end)
            return True

    return False

def get_environment_reserved_time_slots(
        environment_id: Union[int, str], 
        existing_bookings: Dict[str, List[Dict[str, Union[str, datetime]]]]) -> List[Dict]:
    
    free_time_slots = []
    environment_id = str(environment_id)
    
    return free_time_slots


@tool("book_environment", description="Book a environment for the specified time and user.")
def book_environment_tool(
        environment_id: int, start_time: str, 
        end_time: str, user_name: str
    ) -> Optional[dict]:
    """Book a environment_id for the specified time and user."""
    existing_bookings = load_bookings()

    logger.info("existing booking value: %s (%s)", existing_bookings, type(existing_bookings))

    if check_time_conflict_tool(
        existing_bookings,environment_id, start_time, duration_hours=int((datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 3600)
    ):
        return None
    
    logger.info("Booking environment %s for user %s from %s to %s", environment_id, user_name, start_time, end_time)

    booking = {
        "environment_id": environment_id,
        "start_time": start_time,
        "end_time": end_time,
        "booked_by": user_name,
    }

    # # Ensure the environment_id has a booking list
    # if environment_id not in existing_bookings:
    #     existing_bookings[environment_id] = []

    # # Append the Booking object
    # existing_bookings[environment_id].append(booking)

    # existing_bookings.append(booking)
    save_bookings_tool(environment_id, booking)

    logger.info("booking is completed")
    return booking

