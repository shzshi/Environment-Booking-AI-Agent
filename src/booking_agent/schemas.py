# src/booking_agent/schemas.py
"""Pydantic models for data validation in booking environments."""
import re
from datetime import datetime
from pydantic import BaseModel, RootModel, Field, field_validator
from typing_extensions import TypedDict
from typing import Union, List, Dict, Optional, Literal
from langchain_core.messages import HumanMessage, SystemMessage


## Agent State Definition as a TypedDict
class AgentState(TypedDict):
    # Core Conversation
    user_input: str
    messages: List[Union[HumanMessage, SystemMessage]]  # Chat history
    
    # Request Processing
    parsed_request: Optional[Dict]         # Structured request: {date, times, attendees, tool}
    clarification_needed: bool             # Flag for missing info
    clarification_question: Optional[str]  
    user_name_for_booking: Optional[str]   
    
    # Environment Selection
    matching_environments: Optional[List[Dict]]    # Environments matching requirements
    available_environments: Optional[List[Dict]]   # Filtered by availability
    alternative_environments: Optional[List[Dict]] # Fallback options
    selected_environment: Optional[Dict]           # User's final choice
    user_confirmation: Optional[Literal["yes", "no"]]  # Explicit confirmation
    
    # Booking Result
    booking_result: Optional[bool]     # Flag for confirmed booking
    error_message: Optional[str]       # Error details if booking fails

class Environment(BaseModel):
    """Model for a environment."""
    id: int = Field(description="Unique identifier for the environment")
    name: str = Field(description="Name of the environment")
    purpose: str = Field(description="What is the purpose of booking the environment")
    tools: List[str] = Field(description="List of tool available in the environment")
    location: Optional[str] = Field(default=None, description="Physical location of the environment")
    amenities: Optional[List[str]] = Field(default_factory=list, description="Additional amenities")

class Booking(BaseModel):
    """Model for a booking record."""
    environment_id: int = Field(description="ID of the environment being booked")
    start_time: str = Field(description="Start time of the booking in ISO format")
    end_time: str = Field(description="End time of the booking in ISO format")
    booked_by: str = Field(description="Name of the person making the booking")
    purpose: Optional[str] = Field(default=None, description="Purpose of the booking")
    attendees: Optional[int] = Field(default=None, description="Number of attendees")

class BookingRequest(BaseModel):
    environment_type: Optional[str] = Field(
        None,
        description="Environment type such as dev, qa, performance, release, preprod."
    )
    start_date: Optional[str] = Field(
        None,
        description="The starting date for the booking in the format YYYY-MM-DD (e.g., 2025-05-12)" \
        "This can be a specific date or derived from relative terms like 'tomorrow'." \
        "This date must be in future."
    )
    start_time: Optional[str] = Field(
        None,
        description="The starting time for the booking in the format HH:MM:SS AM/PM (e.g., 02:45:30 PM). " \
        "This can be a specific time or calculated from relative terms like 'after 1 hour'."\
        "The time must be in future." \
    )
    duration_hours: Optional[float] = Field(
        None,
        description="The duration of the booking in hours (e.g., 0.5 for 30 minutes, 1 for one hour)." \
        " Accepts fractional values for partial hours."
    )
    purpose: Optional[str] = Field(
        None,
        description="The purpose of the booking (e.g., environment for development, QA, performance, or release validation?)."
    )
    tools: Optional[List[str]] = Field(
        default_factory=list,  # Default to an empty list if no value is provided
        description="A list of tool required for the booking (e.g., ['Jenkins', 'Grafana'])."\
        "If user don't have specific tools, write 'nothing'."
    )
    user_name: Optional[str] = Field(
        None,
        description="The name of the person making the booking to personalize the booking process."
    )
    clarification_needed: bool = Field(
        False,
        description="Indicates whether additional clarification is required to process the booking request"\
         " (e.g., True if the input is ambiguous or incomplete)."
    )
    clarification_question: Optional[str] = Field(
        None,
        description="A question to ask the user for clarification if required fields are nulls or ambiguous"\
             " (e.g., 'Could you specify the start time?')."
    )

    # @field_validator("start_date")
    # def validate_start_date(cls, v):
    #     if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
    #         raise ValueError("start_date must be in YYYY-MM-DD format")
    #     return v

    # @field_validator("start_time")
    # def normalize_start_time(cls, v):
    #     if not v:
    #         return v
    #     # Handle cases like "2 PM" or "10:30 PM"
    #     match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", v, re.IGNORECASE)
    #     if match:
    #         hour, minute, period = match.groups()
    #         hour = hour.zfill(2)  # Pad hour to two digits
    #         minute = minute or "00"  # Default to 00 if no minutes
    #         return f"{hour}:{minute}:00 {period.upper()}"
    #     # Validate strict HH:MM:SS AM/PM
    #     if not re.match(r"^\d{2}:\d{2}:\d{2} (AM|PM)$", v, re.IGNORECASE):
    #         raise ValueError("start_time must be in HH:MM:SS AM/PM format")
    #     return v.upper()

