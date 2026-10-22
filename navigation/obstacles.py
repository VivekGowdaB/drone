import math
from sim.vec3 import Vec3

class Obstacle:
    """Base class for environment obstacles."""
    def is_inside(self, point: Vec3) -> bool:
        raise NotImplementedError

    def distance_to(self, point: Vec3) -> float:
        raise NotImplementedError

class SphereObstacle(Obstacle):
    def __init__(self, center: Vec3, radius: float):
        self.center = Vec3(center)
        self.radius = radius

    def is_inside(self, point: Vec3) -> bool:
        return (Vec3(point) - self.center).length() <= self.radius

    def distance_to(self, point: Vec3) -> float:
        d = (Vec3(point) - self.center).length() - self.radius
        return max(0.0, d)

class BoxObstacle(Obstacle):
    def __init__(self, center: Vec3, size: Vec3):
        self.center = Vec3(center)
        self.half_size = Vec3(size) * 0.5

    def is_inside(self, point: Vec3) -> bool:
        p = Vec3(point) - self.center
        return (abs(p.x) <= self.half_size.x and
                abs(p.y) <= self.half_size.y and
                abs(p.z) <= self.half_size.z)

    def distance_to(self, point: Vec3) -> float:
        p = Vec3(point) - self.center
        dx = max(abs(p.x) - self.half_size.x, 0.0)
        dy = max(abs(p.y) - self.half_size.y, 0.0)
        dz = max(abs(p.z) - self.half_size.z, 0.0)
        return math.sqrt(dx*dx + dy*dy + dz*dz)

class CylinderObstacle(Obstacle):
    def __init__(self, center_base: Vec3, radius: float, height: float):
        self.center_base = Vec3(center_base)
        self.radius = radius
        self.height = height

    def is_inside(self, point: Vec3) -> bool:
        p = Vec3(point)
        dy = p.y - self.center_base.y
        if dy < 0 or dy > self.height:
            return False
        dx = p.x - self.center_base.x
        dz = p.z - self.center_base.z
        return (dx*dx + dz*dz) <= self.radius*self.radius

    def distance_to(self, point: Vec3) -> float:
        p = Vec3(point)
        dx = p.x - self.center_base.x
        dz = p.z - self.center_base.z
        d_horizontal = max(math.sqrt(dx*dx + dz*dz) - self.radius, 0.0)
        
        dy = p.y - self.center_base.y
        d_vertical = 0.0
        if dy < 0:
            d_vertical = -dy
        elif dy > self.height:
            d_vertical = dy - self.height
            
        return math.sqrt(d_horizontal*d_horizontal + d_vertical*d_vertical)
