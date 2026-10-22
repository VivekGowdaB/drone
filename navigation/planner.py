from sim.vec3 import Vec3
from navigation.environment import Environment
from navigation.planning_result import PlanningResult

class Planner:
    """Abstract Planner interface."""
    
    def plan(self, start: Vec3, goal: Vec3, env: Environment) -> PlanningResult:
        raise NotImplementedError
        
    def replan(self) -> PlanningResult:
        raise NotImplementedError
        
    def validate_path(self, env: Environment) -> bool:
        raise NotImplementedError
        
    def estimate_cost(self, start: Vec3, goal: Vec3) -> float:
        return (Vec3(goal) - Vec3(start)).length()
