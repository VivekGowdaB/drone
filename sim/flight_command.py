from sim.vec3 import Vec3

class FlightCommand:
    """The desired control inputs requested by the flight controller."""
    def __init__(self):
        self.desired_velocity = Vec3(0, 0, 0) # For legacy compatibility with collision avoidance
        self.thrust_vector = Vec3(0, 0, 0)
        self.desired_heading = Vec3(0, 0, 1)
        self.priority = 1.0
