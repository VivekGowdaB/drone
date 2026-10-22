import time
from sim.vec3 import Vec3
from navigation.planner import Planner
from navigation.environment import Environment
from navigation.planning_result import PlanningResult
from navigation.path import Path

class StraightLinePlanner(Planner):
    def plan(self, start: Vec3, goal: Vec3, env: Environment) -> PlanningResult:
        t0 = time.time()
        
        path_obj = None
        success = env.is_path_valid(start, goal)
        if success:
            path_obj = Path([start, goal], planner_name="Straight")
            
        result = PlanningResult(path_obj, "Straight", success)
        result.planning_time = time.time() - t0
        result.nodes_expanded = 2
        result.iterations = 1
        return result
