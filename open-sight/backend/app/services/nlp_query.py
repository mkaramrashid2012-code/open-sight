"""
OpenSight Enterprise - Natural Language Query Engine
Converts natural language queries into structured search filters.
Example: "Find people who entered the back door after midnight" 
       -> {object: "person", zone: "back_door", time_start: "00:00", event: "entry"}
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

class NaturalLanguageQueryParser:
    def __init__(self):
        # Synonym mappings
        self.object_synonyms = {
            "person": ["person", "people", "man", "woman", "human", "individual", "pedestrian"],
            "vehicle": ["vehicle", "car", "truck", "van", "bus", "automobile", "auto"],
            "bicycle": ["bicycle", "bike", "cyclist"],
            "bag": ["bag", "backpack", "suitcase", "luggage", "package"],
            "animal": ["animal", "dog", "cat", "pet"]
        }
        
        self.event_synonyms = {
            "entry": ["enter", "entered", "entrance", "in", "coming in"],
            "exit": ["exit", "exited", "leave", "leaving", "out", "going out"],
            "loitering": ["loiter", "loitering", "lingering", "hanging around", "waiting"],
            "intrusion": ["intrude", "intrusion", "trespass", "unauthorized"],
            "running": ["run", "running", "sprint", "sprinting", "jogging"],
            "fall": ["fall", "fallen", "collapse", "collapsed"],
            "crossing": ["cross", "crossing", "passed through"]
        }
        
        self.direction_synonyms = {
            "left": ["left", "west", "leftward"],
            "right": ["right", "east", "rightward"],
            "up": ["up", "north", "upward", "top"],
            "down": ["down", "south", "downward", "bottom"]
        }
        
        self.zone_keywords = ["zone", "area", "region", "door", "gate", "entrance", "exit", "parking", "lobby", "hallway", "room"]

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured format.
        
        Args:
            query: Natural language string
            
        Returns:
            Structured query dictionary
        """
        query_lower = query.lower()
        structured = {
            "original_query": query,
            "filters": {},
            "confidence": 0.0,
            "explanation": []
        }
        
        # Extract object type
        obj_type = self._extract_object(query_lower)
        if obj_type:
            structured["filters"]["object_class"] = obj_type
            structured["explanation"].append(f"Looking for {obj_type}")
            
        # Extract event/action
        event = self._extract_event(query_lower)
        if event:
            structured["filters"]["event_type"] = event
            structured["explanation"].append(f"Performing action: {event}")
            
        # Extract time constraints
        time_constraints = self._extract_time(query_lower)
        if time_constraints:
            structured["filters"].update(time_constraints)
            if "time_start" in time_constraints:
                structured["explanation"].append(f"After {time_constraints['time_start']}")
            if "time_end" in time_constraints:
                structured["explanation"].append(f"Before {time_constraints['time_end']}")
                
        # Extract direction
        direction = self._extract_direction(query_lower)
        if direction:
            structured["filters"]["direction"] = direction
            structured["explanation"].append(f"Moving {direction}")
            
        # Extract zone/location (simplified - would need zone registry in production)
        zone = self._extract_zone(query_lower)
        if zone:
            structured["filters"]["zone"] = zone
            structured["explanation"].append(f"In zone: {zone}")
            
        # Extract attributes (color, etc.)
        attributes = self._extract_attributes(query_lower)
        if attributes:
            structured["filters"]["attributes"] = attributes
            structured["explanation"].append(f"With attributes: {attributes}")
            
        # Calculate confidence based on how many elements were extracted
        elements_found = sum([
            1 if obj_type else 0,
            1 if event else 0,
            1 if time_constraints else 0,
            1 if direction else 0,
            1 if zone else 0
        ])
        structured["confidence"] = min(1.0, elements_found / 3.0)  # Need at least 3 for high confidence
        
        return structured

    def _extract_object(self, query: str) -> Optional[str]:
        """Extract object class from query."""
        for obj_type, synonyms in self.object_synonyms.items():
            for synonym in synonyms:
                if re.search(rf'\b{synonym}\b', query):
                    return obj_type
        return None

    def _extract_event(self, query: str) -> Optional[str]:
        """Extract event type from query."""
        for event, synonyms in self.event_synonyms.items():
            for synonym in synonyms:
                if synonym in query:
                    return event
        return None

    def _extract_time(self, query: str) -> Optional[Dict[str, str]]:
        """Extract time constraints from query."""
        time_constraints = {}
        
        # Patterns for time extraction
        patterns = [
            (r'after\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?', 'start'),
            (r'before\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?', 'end'),
            (r'between\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?\s+and\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?', 'range'),
            (r'around\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?', 'approx'),
            (r'midnight', 'midnight'),
            (r'noon', 'noon'),
            (r'morning', 'morning'),
            (r'evening', 'evening'),
            (r'night', 'night')
        ]
        
        for pattern, constraint_type in patterns:
            match = re.search(pattern, query)
            if match:
                if constraint_type == 'start':
                    time_str = self._normalize_time(match.group(1), match.group(2), match.group(3))
                    time_constraints['time_start'] = time_str
                elif constraint_type == 'end':
                    time_str = self._normalize_time(match.group(1), match.group(2), match.group(3))
                    time_constraints['time_end'] = time_str
                elif constraint_type == 'range':
                    time_constraints['time_start'] = self._normalize_time(match.group(1), match.group(2), match.group(3))
                    time_constraints['time_end'] = self._normalize_time(match.group(4), match.group(5), match.group(6))
                elif constraint_type == 'midnight':
                    time_constraints['time_start'] = '00:00'
                    time_constraints['time_end'] = '06:00'
                elif constraint_type == 'noon':
                    time_constraints['time_start'] = '12:00'
                    time_constraints['time_end'] = '13:00'
                elif constraint_type == 'morning':
                    time_constraints['time_start'] = '06:00'
                    time_constraints['time_end'] = '12:00'
                elif constraint_type == 'evening':
                    time_constraints['time_start'] = '17:00'
                    time_constraints['time_end'] = '22:00'
                elif constraint_type == 'night':
                    time_constraints['time_start'] = '22:00'
                    time_constraints['time_end'] = '23:59'
                    
        return time_constraints if time_constraints else None

    def _normalize_time(self, hour: str, minute: Optional[str], ampm: Optional[str]) -> str:
        """Normalize time to HH:MM format."""
        h = int(hour)
        m = int(minute) if minute else 0
        
        if ampm:
            if ampm.lower() == 'pm' and h != 12:
                h += 12
            elif ampm.lower() == 'am' and h == 12:
                h = 0
                
        return f"{h:02d}:{m:02d}"

    def _extract_direction(self, query: str) -> Optional[str]:
        """Extract direction from query."""
        for direction, synonyms in self.direction_synonyms.items():
            for synonym in synonyms:
                if re.search(rf'\b{synonym}\b', query):
                    return direction
        return None

    def _extract_zone(self, query: str) -> Optional[str]:
        """Extract zone reference from query."""
        # Look for patterns like "back door", "main entrance", "parking lot"
        zone_patterns = [
            r'(back|front|side|main|emergency)\s+(door|gate|entrance|exit)',
            r'(parking\s+(lot|garage|area))',
            r'(lobby|hallway|corridor|room\s+\w+)',
            r'(restricted\s+(area|zone))',
            r'(reception|desk|counter)'
        ]
        
        for pattern in zone_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0).strip()
                
        return None

    def _extract_attributes(self, query: str) -> Dict[str, str]:
        """Extract attributes like color, size from query."""
        attributes = {}
        
        # Color patterns
        colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'orange', 'purple', 'gray', 'grey', 'brown']
        for color in colors:
            if re.search(rf'\b{color}\b', query):
                attributes['color'] = color
                break
                
        # Size patterns
        sizes = ['large', 'big', 'small', 'tiny', 'huge', 'tall', 'short']
        for size in sizes:
            if re.search(rf'\b{size}\b', query):
                attributes['size'] = size
                break
                
        return attributes if attributes else {}

# Example usage
if __name__ == "__main__":
    parser = NaturalLanguageQueryParser()
    
    test_queries = [
        "Find people who entered the back door after midnight",
        "Show me red cars in the parking lot between 2pm and 4pm",
        "Person running in the hallway during evening",
        "Vehicle moving left near the main entrance"
    ]
    
    for q in test_queries:
        result = parser.parse(q)
        print(f"\nQuery: {q}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Filters: {result['filters']}")
        print(f"Explanation: {'; '.join(result['explanation'])}")
