import random
import math
from time import perf_counter
from config import *
from sim.drone_model import DroneModel
from sim.spatial_index import SpatialHashGrid
from sim.collision_avoidance import CollisionAvoidance
from sim.vec3 import Vec3
from missions.mission_types import (
    HoverMission,
    WaypointMission,
    PatrolMission,
    ReturnHomeMission,
    PlannedMission,
)
from missions.mission_assignment import MissionAssignment
from missions.mission_manager import MissionManager
from missions.mission import MissionStatus
from missions.waypoint import Waypoint
from navigation.environment import Environment
class SwarmModel:
    """Pure simulation model for the entire swarm.
    Holds the DroneModels and SpatialHashGrid,
    decoupled from any rendering.
    """
    def __init__(self, environment=None, num_drones=0):
        self.drones = []
        self.grid = SpatialHashGrid(cell_size=GRID_CELL_SIZE)
        self.collision_avoidance = CollisionAvoidance()
        self.mission_manager = MissionManager()
        self.environment = (
            environment if environment is not None else Environment()
        )
        self._next_drone_id = 1
        # Performance profiling
        self._frame = 0
        self._sample_interval = 60
        self._last_naive_time = 0.0
        self._last_grid_time = 0.0
        if num_drones > 0:
            self.spawn_drones(num_drones)
    def spawn_drones(self, count):
        """Create drones at random positions."""
        new_drones = []
        for _ in range(count):
            position = (
                random.uniform(-25, 25),
                random.uniform(5, 12),
                random.uniform(-25, 25),
            )
            readable_id = f"UAV-{self._next_drone_id:03d}"
            self._next_drone_id += 1
            drone_model = DroneModel(
                position=position,
                readable_id=readable_id,
            )
            self.drones.append(drone_model)
            self.grid.insert(drone_model)
            new_drones.append(drone_model)
            # Drones start idle; no automatic mission assignment.
        return new_drones
    def remove_drone(self, drone_id):
        """Remove a drone and cancel its assigned mission."""
        for drone in self.drones:
            if drone.id == drone_id:
                self.drones.remove(drone)
                self.grid.remove(drone)
                self.mission_manager.cancel_mission(drone.id)
                return True
        return False
    def update(self, dt: float, physics_engine, environment=None):
        """Advance the swarm simulation by one tick."""
        self._frame += 1
        # Periodically compare naive neighbor searching with the spatial grid.
        if self._frame % self._sample_interval == 0:
            n = len(self.drones)
            # Naive O(N^2) neighbor search.
            t0 = perf_counter()
            for drone in self.drones:
                neighbors = []
                for other_drone in self.drones:
                    if other_drone is drone:
                        continue
                    distance = (
                        drone.position - other_drone.position
                    ).length()
                    if distance < SAFE_DISTANCE:
                        neighbors.append(other_drone)
            t1 = perf_counter()
            self._last_naive_time = t1 - t0
            # Spatial-grid neighbor search.
            t0 = perf_counter()
            for drone in self.drones:
                self.grid.query_radius(drone.position, SAFE_DISTANCE)
            t1 = perf_counter()
            self._last_grid_time = t1 - t0
            if DEBUG_MODE:
                print(
                    f"[spatial_index] N={n} "
                    f"naive={self._last_naive_time:.6f}s "
                    f"grid={self._last_grid_time:.6f}s"
                )
        # Advance missions and retrieve active waypoints.
        drone_states_dict = {
            drone.id: drone.position for drone in self.drones
        }
        active_waypoints = self.mission_manager.update(
            dt, drone_states_dict
        )
        # Update each drone.
        active_environment = (
            environment if environment is not None else self.environment
        )
        for drone in self.drones:
            # 1. Find nearby drones.
            neighbors = self.grid.query_radius(
                drone.position, SAFE_DISTANCE
            )
            neighbor_positions = [
                other.position
                for other in neighbors
                if other is not drone
            ]
            # 2. Update high-level drone logic.
            drone.update_logic()
            # 3. Generate the desired flight command.
            active_waypoint = active_waypoints.get(drone.id)
            command = drone.controller.update(
                dt,
                active_waypoint=active_waypoint,
            )
            # 4. Apply collision avoidance.
            safe_command = self.collision_avoidance.process(
                command,
                drone.state,
                neighbor_positions,
            )
            # 5. Apply physics and environmental constraints.
            physics_engine.step(
                drone.state,
                safe_command,
                dt,
                active_environment,
            )
            # 6. Update spatial-grid membership.
            self.grid.update(drone)
    def get_drone(self, drone_id):
        """Return a drone by its ID, or None if it does not exist."""
        for drone in self.drones:
            if drone.id == drone_id:
                return drone
        return None
    def assign_hover(self, drone_id):
        """Assign a hover mission to a drone."""
        drone = self.get_drone(drone_id)
        if drone:
            mission = HoverMission(
                position=drone.position,
                altitude=drone.position.y,
            )
            assignment = MissionAssignment(drone_id, mission)
            self.mission_manager.assign_mission(drone_id, assignment)
            self.mission_manager.start_mission(drone_id)
    def assign_waypoint(self, drone_id):
        """Assign a randomly generated nearby waypoint."""
        drone = self.get_drone(drone_id)
        if drone:

            from config import WORLD_LIMIT

            margin = 2.0  # safety buffer from the border

            wx = drone.position.x + random.uniform(-15, 15)

            wz = drone.position.z + random.uniform(-15, 15)

            wx = max(-WORLD_LIMIT + margin, min(wx, WORLD_LIMIT - margin))

            wz = max(-WORLD_LIMIT + margin, min(wz, WORLD_LIMIT - margin))

            wp_pos = Vec3(wx, drone.position.y, wz)

            wp = Waypoint("rand_wp", position=wp_pos)

            mission = WaypointMission([wp])

            assignment = MissionAssignment(drone_id, mission)
            self.mission_manager.assign_mission(drone_id, assignment)
            self.mission_manager.start_mission(drone_id)
    def assign_patrol(self, drone_id):
        """Assign a circular patrol mission to a drone."""
        drone = self.get_drone(drone_id)
        if drone:

            import math

            from config import WORLD_LIMIT

            radius = 15.0
            margin = 2.0  # safety buffer so patrol circle doesn't hug the border
            min_bound = -WORLD_LIMIT + radius + margin
            max_bound = WORLD_LIMIT - radius - margin
            # If world is too small for this radius, shrink radius to fit
            if min_bound > max_bound:
                radius = max(2.0, WORLD_LIMIT - margin)
                min_bound = -WORLD_LIMIT + radius + margin
                max_bound = WORLD_LIMIT - radius - margin
            cx = max(min_bound, min(drone.position.x, max_bound))
            cz = max(min_bound, min(drone.position.z, max_bound))
            center = Vec3(cx, drone.position.y, cz)
            waypoints = []
            num_points = 4
            for i in range(num_points):
                angle = (2 * math.pi / num_points) * i

                waypoint_x = center.x + radius * math.cos(angle)

                waypoint_z = center.z + radius * math.sin(angle)

                waypoint = Waypoint(

                    f"patrol_{i}",

                    position=Vec3(

                        waypoint_x,

                        center.y,

                        waypoint_z,

                    ),

                )

                waypoints.append(waypoint)

            mission = PatrolMission(waypoints)
            assignment = MissionAssignment(drone_id, mission)
            self.mission_manager.assign_mission(drone_id, assignment)
            self.mission_manager.start_mission(drone_id)
    def assign_return_home(self, drone_id):
        """Assign a return-to-home mission to a drone."""
        drone = self.get_drone(drone_id)
        if drone:
            mission = ReturnHomeMission(
                home_position=drone.home_position,
                return_altitude=15.0,
            )
            assignment = MissionAssignment(drone_id, mission)
            self.mission_manager.assign_mission(drone_id, assignment)

            self.mission_manager.start_mission(drone_id)

    def assign_planned_mission(

        self,

        drone_id,

        planner_name,

        destination,

    ):

        """Plan a path and assign it as a mission to a drone."""

        drone = self.get_drone(drone_id)

        if drone is None:

            return False, "Drone not found."

        mission = PlannedMission(

            start=drone.position,

            goal=destination,

            env=self.environment,

            planner_name=planner_name,

        )

        if mission.status == MissionStatus.FAILED:

            return False, "Path planning failed."

        assignment = MissionAssignment(drone_id, mission)

        self.mission_manager.assign_mission(drone_id, assignment)

        self.mission_manager.start_mission(drone_id)

        return True, "Path generated successfully."
