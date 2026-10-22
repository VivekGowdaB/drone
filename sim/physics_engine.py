from sim.flight_command import FlightCommand
from sim.drone_state import DroneState
from sim.vec3 import Vec3, lerp
from config import WORLD_LIMIT, MIN_HEIGHT, MAX_HEIGHT

class PhysicsEngine:
    """Stateless engine for numerical integration of motion."""
    
    def step(self, state: DroneState, command: FlightCommand, dt: float, environment=None):
        """Applies true physical forces and checks collisions."""
        from config import GRAVITY, DRONE_MASS, MAX_THRUST, DRAG_COEFFICIENT, WORLD_LIMIT, MIN_HEIGHT
        import math
        
        if dt <= 0:
            return
            
        # 1. Cap thrust
        thrust = command.thrust_vector
        if thrust.length() > MAX_THRUST:
            thrust = thrust.normalized() * MAX_THRUST
            
        # 2. Compute Forces
        gravity_force = Vec3(0, -GRAVITY * DRONE_MASS, 0)
        drag_force = -state.velocity * DRAG_COEFFICIENT
        net_force = thrust + gravity_force + drag_force
        
        # 3. Update Kinematics
        state.acceleration = net_force / DRONE_MASS
        state.velocity += state.acceleration * dt
        
        # Limit velocity (terminal velocity or physical max)
        if state.velocity.length() > state.maximum_speed:
            state.velocity = state.velocity.normalized() * state.maximum_speed
            
        new_position = state.position + state.velocity * dt
        
        # 4. Resolve Collisions (Environment)
        collision_occurred = False
        if environment:
            from navigation.obstacles import BoxObstacle
            # Simple collision resolution against BoxObstacles
            for obs in environment.obstacles:
                if isinstance(obs, BoxObstacle):
                    if obs.is_inside(new_position):
                        collision_occurred = True
                        # Find closest face to project out
                        local_p = new_position - obs.center
                        dx = obs.half_size.x - abs(local_p.x)
                        dy = obs.half_size.y - abs(local_p.y)
                        dz = obs.half_size.z - abs(local_p.z)
                        
                        min_dist = min(dx, dy, dz)
                        if min_dist == dx:
                            new_position.x = obs.center.x + (obs.half_size.x if local_p.x > 0 else -obs.half_size.x)
                            state.velocity.x = 0
                        elif min_dist == dy:
                            new_position.y = obs.center.y + (obs.half_size.y if local_p.y > 0 else -obs.half_size.y)
                            state.velocity.y = 0
                        else:
                            new_position.z = obs.center.z + (obs.half_size.z if local_p.z > 0 else -obs.half_size.z)
                            state.velocity.z = 0
                            
        # Ground and Ceiling Bounds
        if new_position.y < MIN_HEIGHT:
            new_position.y = MIN_HEIGHT
            if state.velocity.y < 0: state.velocity.y = 0
            collision_occurred = True
            
        state.position = new_position
        
        # 5. Compute Attitude (Pitch, Roll) based on horizontal thrust required
        # For a quadcopter, thrust is aligned with local Z (up).
        # We tilt the drone to vector thrust horizontally.
        if thrust.length() > 0.1:
            # Angle of thrust vector relative to vertical (Y axis)
            horizontal_thrust = Vec3(thrust.x, 0, thrust.z)
            if horizontal_thrust.length() > 0.01:
                tilt_mag = math.degrees(math.atan2(horizontal_thrust.length(), thrust.y))
                # Clamp tilt to max angle (e.g. 45 degrees)
                tilt_mag = min(tilt_mag, 45.0)
                
                # Decompose into pitch (forward/back) and roll (left/right) relative to heading
                # Simplify by assuming world axes for now, or just mapping to visual rotation
                fwd = state.heading
                right = Vec3(fwd.z, 0, -fwd.x) # Simple 90 deg rotation
                
                thrust_dir = horizontal_thrust.normalized()
                
                # Dot products give the component of tilt along forward and right vectors
                pitch_factor = thrust_dir.dot(fwd)
                roll_factor = thrust_dir.dot(right)
                
                target_pitch = pitch_factor * tilt_mag
                target_roll = roll_factor * tilt_mag
            else:
                target_pitch = 0
                target_roll = 0
        else:
            target_pitch = 0
            target_roll = 0
            
        # Smooth attitude transition
        state.pitch = lerp(state.pitch, target_pitch, min(1.0, 10.0 * dt))
        state.roll = lerp(state.roll, target_roll, min(1.0, 10.0 * dt))
        
        # 6. Smooth Turning (Heading)
        state.heading = lerp(state.heading, command.desired_heading, min(1.0, state.maximum_turn_rate * dt))
        if state.heading.length() > 0:
            state.heading = state.heading.normalized()
