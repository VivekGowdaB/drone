from enum import Enum
from sim.vec3 import Vec3
from config import DRONE_SPEED

class DroneStateEnum(Enum):
    IDLE = "Idle"
    TAKEOFF = "Takeoff"
    CRUISE = "Cruise"
    HOVER = "Hover"
    LANDING = "Landing"
    EMERGENCY = "Emergency"

class DroneState:
    """Holds the physical state and limits of a UAV."""
    def __init__(self, position=(0, 0, 0)):
        self.position = Vec3(*position) if not isinstance(position, Vec3) else position
        self.velocity = Vec3(0, 0, 0)
        self.acceleration = Vec3(0, 0, 0)
        
        # Orientation
        self.heading = Vec3(1, 0, 0)  # Forward vector
        self.pitch = 0.0 # Degrees
        self.roll = 0.0  # Degrees
        
        # Physical constraints
        self.maximum_speed = DRONE_SPEED
        self.maximum_acceleration = 15.0  # arbitrary scale for responsive movement
        self.maximum_turn_rate = 5.0      # arbitrary scale
        
        # State machine
        self.current_state = DroneStateEnum.CRUISE
