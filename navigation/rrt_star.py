import time
import random
from sim.vec3 import Vec3
from navigation.planner import Planner
from navigation.environment import Environment
from navigation.planning_result import PlanningResult
from navigation.path import Path

class Node:
    def __init__(self, pos: Vec3):
        self.pos = pos
        self.parent = None
        self.cost = 0.0

class RRTStarPlanner(Planner):
    def __init__(self, step_size=2.0, search_radius=4.0, max_iter=1000):
        self.step_size = step_size
        self.search_radius = search_radius
        self.max_iter = max_iter

    def get_random_node(self, env, goal):
        if random.random() > 0.1:
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
                
            new_pos = nearest.pos + direction.normalized() * min(self.step_size, dist)
            
            if not env.is_path_valid(nearest.pos, new_pos):
                continue
                
            new_node = Node(new_pos)
            
            # Find neighbors in search_radius
            neighbors = [n for n in nodes if (n.pos - new_pos).length() <= self.search_radius]
            
            # Connect along a minimum-cost path
            min_cost = nearest.cost + (nearest.pos - new_pos).length()
            best_parent = nearest
            
            for n in neighbors:
                if env.is_path_valid(n.pos, new_pos):
                    cost = n.cost + (n.pos - new_pos).length()
                    if cost < min_cost:
                        min_cost = cost
                        best_parent = n
                        
            new_node.parent = best_parent
            new_node.cost = min_cost
            nodes.append(new_node)
            
            # Rewire tree
            for n in neighbors:
                if n == best_parent:
                    continue
                new_cost = new_node.cost + (new_node.pos - n.pos).length()
                if new_cost < n.cost and env.is_path_valid(new_node.pos, n.pos):
                    n.parent = new_node
                    n.cost = new_cost
                    
            if not success and (new_pos - goal).length() <= self.step_size:
                if env.is_path_valid(new_pos, goal):
                    final_node = Node(goal)
                    final_node.parent = new_node
                    final_node.cost = new_node.cost + (new_node.pos - goal).length()
                    nodes.append(final_node)
                    success = True
                    # In true RRT* we continue to optimize until max_iter.
                    # For performance in python, we might break, but let's just keep going.
                    
        path_list = []
        if success:
            goal_nodes = [n for n in nodes if (n.pos - goal).length() < 0.1]
            if not goal_nodes:
                goal_nodes = [final_node]
                
            best_goal = min(goal_nodes, key=lambda n: n.cost)
            curr = best_goal
            while curr is not None:
                path_list.append(curr.pos)
                curr = curr.parent
            path_list.reverse()
            
        path_obj = Path(path_list, planner_name="RRT*") if success else None
        
        result = PlanningResult(path_obj, "RRT*", success)
        result.planning_time = time.time() - t0
        result.nodes_expanded = len(nodes)
        result.iterations = i + 1
        return result
