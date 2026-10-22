from sim.vec3 import Vec3
from typing import Dict, Any

class Waypoint:
    """A navigational goal for a UAV."""
    def __init__(self, waypoint_id: str, position: Vec3, altitude: float = None,
                 acceptance_radius: float = 1.0, desired_speed: float = 4.0,
                 desired_heading: Vec3 = None, hold_time: float = 0.0,
                 metadata: Dict[str, Any] = None):
        self.id = waypoint_id
        
        # If altitude is provided, override the Y component of position
        self.position = Vec3(position)
        if altitude is not None:
            self.position.y = altitude
            
        self.acceptance_radius = acceptance_radius
        self.desired_speed = desired_speed
        self.desired_heading = desired_heading
        self.hold_time = hold_time
        self.metadata = metadata or {}
