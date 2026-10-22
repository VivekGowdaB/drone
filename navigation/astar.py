import time
import heapq
from sim.vec3 import Vec3
from navigation.planner import Planner
from navigation.environment import Environment
from navigation.planning_result import PlanningResult
from navigation.path import Path

class AStarPlanner(Planner):
    def __init__(self, step_size=2.0):
        self.step_size = step_size
        
    def plan(self, start: Vec3, goal: Vec3, env: Environment) -> PlanningResult:
        t0 = time.time()
        
        def get_neighbors(pos):
            neighbors = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        n_pos = Vec3(pos.x + dx*self.step_size, 
                                     pos.y + dy*self.step_size, 
                                     pos.z + dz*self.step_size)
                        neighbors.append(n_pos)
            return neighbors

        def to_tuple(v: Vec3):
            return (round(v.x/self.step_size), round(v.y/self.step_size), round(v.z/self.step_size))
            
        open_set = []
        heapq.heappush(open_set, (0.0, to_tuple(start), start))
        
        came_from = {}
        g_score = {to_tuple(start): 0.0}
        
        nodes_expanded = 0
        success = False
        final_node = None
        
        while open_set:
            if time.time() - t0 > 2.0: # Timeout
                break
                
            _, current_tuple, current_vec = heapq.heappop(open_set)
            nodes_expanded += 1
            
            if (current_vec - goal).length() < self.step_size * 1.5:
                # Target reached
                success = True
                final_node = current_tuple
                break
                
            for neighbor in get_neighbors(current_vec):
                if not env.is_point_valid(neighbor): # Faster than path_valid for grid
                    continue
                    
                n_tuple = to_tuple(neighbor)
                tentative_g = g_score[current_tuple] + (neighbor - current_vec).length()
                
                if n_tuple not in g_score or tentative_g < g_score[n_tuple]:
                    came_from[n_tuple] = (current_tuple, current_vec)
                    g_score[n_tuple] = tentative_g
                    f_score = tentative_g + (neighbor - goal).length()
                    heapq.heappush(open_set, (f_score, n_tuple, neighbor))
                    
        path_list = []
        if success:
            path_list.append(goal)
            curr = final_node
            while curr in came_from:
                curr, curr_vec = came_from[curr]
                path_list.append(curr_vec)
            path_list.reverse()
            path_list[0] = start # Ensure exact start
            
        path_obj = Path(path_list, planner_name="A*") if success else None
        
        result = PlanningResult(path_obj, "A*", success)
        result.planning_time = time.time() - t0
        result.nodes_expanded = nodes_expanded
        result.iterations = nodes_expanded
        return result
