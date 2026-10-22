import time
import random
from sim.vec3 import Vec3
from navigation.planner import Planner
from navigation.environment import Environment
from navigation.planning_result import PlanningResult
from navigation.path import Path

class Node:
    def __init__(self, pos: Vec3, parent=None):
        self.pos = pos
        self.parent = parent

class RRTPlanner(Planner):
    def __init__(self, step_size=2.0, max_iter=2000):
        self.step_size = step_size
        self.max_iter = max_iter

    def get_random_node(self, env, goal):
        if random.random() > 0.1: # 10% goal bias
            x = random.uniform(env.min_bounds.x, env.max_bounds.x)
            y = random.uniform(env.min_bounds.y, env.max_bounds.y)
            z = random.uniform(env.min_bounds.z, env.max_bounds.z)
            return Vec3(x, y, z)
        return goal

    def plan(self, start: Vec3, goal: Vec3, env: Environment) -> PlanningResult:
        t0 = time.time()
        
        nodes = [Node(start)]
        success = False
        final_node = None
        
        i = 0
        for i in range(self.max_iter):
            rnd = self.get_random_node(env, goal)
            nearest = min(nodes, key=lambda n: (n.pos - rnd).length())
            
            direction = rnd - nearest.pos
            dist = direction.length()
            if dist == 0:
                continue
                
            direction = direction.normalized()
            new_pos = nearest.pos + direction * min(self.step_size, dist)
            
            if env.is_path_valid(nearest.pos, new_pos):
                new_node = Node(new_pos, nearest)
                nodes.append(new_node)
                
                if (new_pos - goal).length() <= self.step_size:
                    if env.is_path_valid(new_pos, goal):
                        final_node = Node(goal, new_node)
                        nodes.append(final_node)
                        success = True
                        break
                        
        path_list = []
        if success:
            curr = final_node
            while curr is not None:
                path_list.append(curr.pos)
                curr = curr.parent
            path_list.reverse()
            
        path_obj = Path(path_list, planner_name="RRT") if success else None
        
        result = PlanningResult(path_obj, "RRT", success)
        result.planning_time = time.time() - t0
        result.nodes_expanded = len(nodes)
        result.iterations = i + 1
        return result
