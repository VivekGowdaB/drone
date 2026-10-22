import uuid
import random
from sim.vec3 import Vec3
from config import *
from sim.drone_state import DroneState
from sim.flight_controller import FlightController

class DroneModel:
    """Represents a single UAV in the simulation, owning its state and controllers."""

    def __init__(self, position=(0, 5, 0), readable_id="UAV-000"):
        self.uuid = str(uuid.uuid4())
        self.id = self.uuid # for backwards compatibility
        self.readable_id = readable_id
        
        # Every DroneModel maintains its own home_position
        self.home_position = Vec3(*position) if not isinstance(position, Vec3) else position
        
        # Core physical state
        self.state = DroneState(position=position)
        
        # High-level motion planner
        self.controller = FlightController(self.state)

    def update_logic(self):
        """Called by SwarmModel. Waypoint transition logic is now in MissionManager."""
        pass

    # Properties to maintain compatibility with view layer (drone.py)
    @property
    def position(self):
        return self.state.position
        
    @property
    def heading(self):
        return self.state.heading

