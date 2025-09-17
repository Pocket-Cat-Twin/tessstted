"""Voice-to-AI Streaming System

Real-time voice processing system with invisible overlay for AI responses.
"""

__version__ = "1.0.0"
__author__ = "Voice-AI System"

from .core.state_manager import StateManager
from .core.event_bus import EventBus

__all__ = ["StateManager", "EventBus"]