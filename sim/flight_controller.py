from sim.flight_command import FlightCommand
from missions.waypoint import Waypoint
from sim.vec3 import Vec3

class FlightController:
    """Converts high-level navigation goals (Waypoints) into a FlightCommand."""
    def __init__(self, drone_state):
        self.state = drone_state
        self.is_stopped = False

    def stop(self):
        self.is_stopped = True

    def resume(self):
        self.is_stopped = False

    def update(self, dt: float, active_waypoint: Waypoint = None) -> FlightCommand:
        """Calculates desired movement and thrust to reach the active waypoint."""
        from config import GRAVITY, DRONE_MASS
        
        command = FlightCommand()
        
        if self.is_stopped or active_waypoint is None:
            # Hover in place
            command.desired_velocity = Vec3(0, 0, 0)
            command.desired_heading = self.state.heading
            command.thrust_vector = Vec3(0, GRAVITY * DRONE_MASS, 0) # Counteract gravity
            return command

        # Position tracking logic
        direction = active_waypoint.position - self.state.position
        dist = direction.length()
        
        if dist > 0:
            direction = direction.normalized()
            
        # Target speed from waypoint, clamped by drone's max capabilities
        speed = min(active_waypoint.desired_speed, self.state.maximum_speed)
        desired_vel = direction * speed
        
        # Simple arrive behavior to prevent overshooting, based on acceptance radius
        arrive_radius = active_waypoint.acceptance_radius + 2.0
        if dist < arrive_radius:
            factor = max(0.0, dist / arrive_radius)
            desired_vel = desired_vel * factor
            
        command.desired_velocity = desired_vel
        
        # Calculate thrust vector (PD controller for velocity)
        # a = Kp * (v_des - v_cur)
        Kp = 2.0
        velocity_error = desired_vel - self.state.velocity
        desired_accel = velocity_error * Kp
        
        # Add gravity compensation
        # F = m * (a - g) where g is downwards, so a + |g| upwards
        gravity_accel = Vec3(0, GRAVITY, 0) 
        command.thrust_vector = (desired_accel + gravity_accel) * DRONE_MASS
        
        # Heading logic
        if active_waypoint.desired_heading is not None:
            command.desired_heading = active_waypoint.desired_heading
        elif desired_vel.length() > 0.1:
            command.desired_heading = Vec3(desired_vel.x, 0, desired_vel.z).normalized()
        else:
            command.desired_heading = self.state.heading
            
        return command
