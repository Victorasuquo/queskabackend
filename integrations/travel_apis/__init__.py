"""
Queska Backend - Travel API Integrations
Provides unified access to travel service providers
"""

from integrations.travel_apis.expedia import (
    expedia_client,
    ExpediaClient,
    ExpediaRapidAPI,
    ExpediaXAPAPI,
)
from integrations.travel_apis.booking_com import (
    booking_com_client,
    BookingComClient,
)
from integrations.travel_apis.rapidapi_hotels import (
    rapidapi_hotels,
    RapidAPIHotelsClient,
)
from integrations.travel_apis.rapidapi_flights import (
    rapidapi_flights,
    RapidAPIFlightsClient,
)

__all__ = [
    # Expedia
    "expedia_client",
    "ExpediaClient",
    "ExpediaRapidAPI",
    "ExpediaXAPAPI",
    # Booking.com
    "booking_com_client",
    "BookingComClient",
    # RapidAPI Hotels (FREE)
    "rapidapi_hotels",
    "RapidAPIHotelsClient",
    # RapidAPI Flights (FREE)
    "rapidapi_flights",
    "RapidAPIFlightsClient",
]


