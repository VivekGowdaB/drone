from typing import List
from sim.vec3 import Vec3
from config import WORLD_LIMIT, MIN_HEIGHT, MAX_HEIGHT
from navigation.obstacles import Obstacle

class Environment:
    """Represents the planning world, providing collision checking."""
    def __init__(self):
        self.obstacles: List[Obstacle] = []
        self.min_bounds = Vec3(-WORLD_LIMIT, MIN_HEIGHT, -WORLD_LIMIT)
        self.max_bounds = Vec3(WORLD_LIMIT, MAX_HEIGHT, WORLD_LIMIT)

    def add_obstacle(self, obstacle: Obstacle):
        self.obstacles.append(obstacle)

    def is_point_valid(self, point: Vec3, clearance: float = 0.5) -> bool:
        """Checks if a point is within bounds and free of obstacles."""
        if (point.x < self.min_bounds.x or point.x > self.max_bounds.x or
            point.y < self.min_bounds.y or point.y > self.max_bounds.y or
            point.z < self.min_bounds.z or point.z > self.max_bounds.z):
            return False
            
        for obs in self.obstacles:
            if obs.distance_to(point) < clearance:
                return False
        return True

    def is_path_valid(self, p1: Vec3, p2: Vec3, step_size: float = 1.0, clearance: float = 0.5) -> bool:
        """Discretized collision check along a line segment."""
        direction = Vec3(p2) - Vec3(p1)
        dist = direction.length()
        
        if dist == 0:
            return self.is_point_valid(p1, clearance)
            
        direction = direction.normalized()
        
        steps = int(dist / step_size)
        for i in range(steps + 1):
            point = Vec3(p1) + direction * (i * step_size)
            if not self.is_point_valid(point, clearance):
                return False
                
        return self.is_point_valid(p2, clearance)
