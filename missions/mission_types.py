from missions.mission import Mission, MissionStatus
from missions.waypoint import Waypoint
from sim.vec3 import Vec3
from navigation.planner_factory import PlannerFactory
from navigation.environment import Environment
from navigation.path_converter import PathConverter

class HoverMission(Mission):
    def __init__(self, position: Vec3, altitude: float = None):
        super().__init__()
        wp = Waypoint("hover_1", position=position, altitude=altitude, hold_time=999999.0)
        self.queue.add_waypoint(wp)

class WaypointMission(Mission):
    def __init__(self, waypoints):
        """waypoints is a list of Waypoint objects"""
        super().__init__()
        for wp in waypoints:
            self.queue.add_waypoint(wp)

class PatrolMission(Mission):
    def __init__(self, waypoints):
        """Loops through waypoints infinitely. waypoints is a list of Waypoint objects."""
        super().__init__()
        self.patrol_waypoints = waypoints
        self._load_waypoints()
        
    def _load_waypoints(self):
        for wp in self.patrol_waypoints:
            self.queue.add_waypoint(wp)

    def update(self, dt: float, drone_position) -> 'Waypoint':
        return super().update(dt, drone_position)

    def complete(self):
        # Instead of completing, just reload the queue and continue running
        if self.status == MissionStatus.RUNNING:
            self._load_waypoints()
            self.active_waypoint = self.queue.peek_next()
        else:
            super().complete()

class ReturnHomeMission(Mission):
    def __init__(self, home_position: Vec3, return_altitude: float = 15.0):
        super().__init__()
        from config import MIN_HEIGHT
        # Direct fly to home at safe altitude, then land
        wp_home = Waypoint("rtl_home", position=home_position, altitude=return_altitude, acceptance_radius=1.0)
        wp_land = Waypoint("rtl_land", position=home_position, altitude=MIN_HEIGHT, acceptance_radius=0.5)
        
        self.queue.add_waypoint(wp_home)
        self.queue.add_waypoint(wp_land)

class PlannedMission(Mission):
    def __init__(self, start: Vec3, goal: Vec3, env: Environment, planner_name: str = "Straight"):
        super().__init__()
        self.planner_name = planner_name
        
        # Request a path from the navigation layer
        planner = PlannerFactory.create_planner(planner_name)
        result = planner.plan(Vec3(start), Vec3(goal), env)
        
        # Convert path to waypoints
        if result.success and result.path and result.path.waypoints:
            self.queue = PathConverter.to_queue(result.path)
            self.status = MissionStatus.CREATED
        else:
            self.status = MissionStatus.FAILED

