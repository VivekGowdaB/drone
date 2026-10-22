from typing import List, Dict, Any
from sim.vec3 import Vec3

class Path:
    """Represents a computed route."""
    def __init__(self, waypoints: List[Vec3], planner_name: str = "Unknown"):
        self.waypoints = waypoints
        self.planner_name = planner_name
        self.metadata: Dict[str, Any] = {}
        
        self.total_length = self._calculate_length()
        
    def _calculate_length(self) -> float:
        length = 0.0
        for i in range(len(self.waypoints) - 1):
            length += (self.waypoints[i+1] - self.waypoints[i]).length()
        return length
