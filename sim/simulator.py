from sim.swarm_model import SwarmModel
from sim.physics_engine import PhysicsEngine

class SimulationClock:
    """Handles time accumulation and fixed timestep logic."""
    def __init__(self, target_hz=60):
        self.target_hz = target_hz
        self.fixed_dt = 1.0 / target_hz
        self.speed_multiplier = 1.0
        
        self.accumulator = 0.0
        self.sim_time = 0.0
        self.real_time = 0.0

    def tick(self, dt):
        """Accumulate real time and return how many fixed ticks to run."""
        self.real_time += dt
        
        # Scale dt by speed multiplier
        scaled_dt = dt * self.speed_multiplier
        
        # Cap max dt to prevent spiral of death if the game hangs
        if scaled_dt > 0.25:
            scaled_dt = 0.25
            
        self.accumulator += scaled_dt
        
        ticks_to_run = int(self.accumulator / self.fixed_dt)
        self.accumulator -= ticks_to_run * self.fixed_dt
        
        return ticks_to_run


class Simulator:
    """Main simulation loop orchestrator.
    
    Can be stepped independently of visualization. Ensures deterministic
    simulation through a fixed timestep.
    """
    def __init__(self, target_hz=60):
        self.clock = SimulationClock(target_hz=target_hz)
        self.physics_engine = PhysicsEngine()
        
        # Centralized Environment (Source of Truth for obstacles)
        from navigation.environment import Environment
        from navigation.obstacles import BoxObstacle
        from sim.vec3 import Vec3
        from config import WORLD_LIMIT, MAX_HEIGHT
        
        self.environment = Environment()
        self._populate_environment()
        
        self.swarm_model = SwarmModel(environment=self.environment)
        # The SwarmModel currently manages the mission manager. We'll pass the environment 
        # to the swarm_model or physics_engine during the step.
        
        self.is_paused = False

    def _populate_environment(self):
        from navigation.obstacles import BoxObstacle, SphereObstacle, CylinderObstacle
        from sim.vec3 import Vec3
        from config import WORLD_LIMIT
        
        # Walls
        thickness = 1
        height = 8
        size = WORLD_LIMIT * 2
        self.environment.add_obstacle(BoxObstacle(center=Vec3(0, height/2, -WORLD_LIMIT), size=Vec3(size, height, thickness)))
        self.environment.add_obstacle(BoxObstacle(center=Vec3(0, height/2, WORLD_LIMIT), size=Vec3(size, height, thickness)))
        self.environment.add_obstacle(BoxObstacle(center=Vec3(-WORLD_LIMIT, height/2, 0), size=Vec3(thickness, height, size)))
        self.environment.add_obstacle(BoxObstacle(center=Vec3(WORLD_LIMIT, height/2, 0), size=Vec3(thickness, height, size)))
        
        # Buildings (Fixed locations and deterministic heights)
        buildings = [
            (Vec3(-20, 0, -15), 6),
            (Vec3(15, 0, -10), 8),
            (Vec3(-10, 0, 18), 10),
            (Vec3(18, 0, 20), 5),
            (Vec3(0, 0, 0), 9)
        ]
        
        for pos, h in buildings:
            self.environment.add_obstacle(BoxObstacle(center=Vec3(pos.x, h/2, pos.z), size=Vec3(4, h, 4)))
            
        # Obstacles for path planning demonstration
        self.environment.add_obstacle(SphereObstacle(Vec3(0, 10, 0), radius=3.0))
        self.environment.add_obstacle(BoxObstacle(Vec3(10, 10, 10), size=Vec3(4, 20, 4)))
        self.environment.add_obstacle(CylinderObstacle(Vec3(-10, 0, -10), radius=2.5, height=20.0))
        
    def pause(self):
        self.is_paused = True
        
    def resume(self):
        self.is_paused = False
        
    def stop(self):
        self.is_paused = True
        # Reset the simulation to initial state
        self.swarm_model = SwarmModel()
        self.clock = SimulationClock(target_hz=self.clock.target_hz)
        
    def step(self):
        """Advance exactly one simulation tick."""
        self.swarm_model.update(self.clock.fixed_dt, self.physics_engine, self.environment)
        self.clock.sim_time += self.clock.fixed_dt
        
    def set_speed(self, speed):
        """Adjusts the simulation speed multiplier (e.g. 0.5, 1.0, 2.0)."""
        self.clock.speed_multiplier = max(0.0, float(speed))
        
    def tick(self, dt):
        """Main update function to be called with external delta time (e.g. from Ursina)."""
        if self.is_paused:
            return
            
        ticks = self.clock.tick(dt)
        for _ in range(ticks):
            self.step()
