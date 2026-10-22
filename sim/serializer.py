import json
from sim.vec3 import Vec3
from sim.drone_state import DroneStateEnum
from navigation.obstacles import BoxObstacle, SphereObstacle, CylinderObstacle
from missions.mission_types import PlannedMission

def vec3_to_dict(v: Vec3) -> dict:
    if v is None:
        return None
    return {"x": v.x, "y": v.y, "z": v.z}

class SimulationSerializer:
    @staticmethod
    def serialize_environment(environment) -> dict:
        obstacles_data = []
        for obs in environment.obstacles:
            if isinstance(obs, BoxObstacle):
                obstacles_data.append({
                    "type": "box",
                    "center": vec3_to_dict(obs.center),
                    "size": vec3_to_dict(obs.half_size * 2) # Ursina scaling logic mapped to raw size
                })
            elif isinstance(obs, SphereObstacle):
                obstacles_data.append({
                    "type": "sphere",
                    "center": vec3_to_dict(obs.center),
                    "radius": obs.radius
                })
            elif isinstance(obs, CylinderObstacle):
                obstacles_data.append({
                    "type": "cylinder",
                    "center_base": vec3_to_dict(obs.center_base),
                    "radius": obs.radius,
                    "height": obs.height
                })

        return {
            "obstacles": obstacles_data
        }

    @staticmethod
    def serialize_uavs(swarm_model, active_assignments) -> list:
        uavs_data = []
        for drone in swarm_model.drones:
            mission = None
            path = None
            target_wp = None
            mission_name = "None"
            mission_status = "Standby"

            if drone.id in active_assignments:
                assignment = active_assignments[drone.id]
                mission_obj = assignment.mission
                mission_name = mission_obj.__class__.__name__
                mission_status = mission_obj.status.value if hasattr(mission_obj.status, 'value') else str(mission_obj.status)

                # active_waypoint is a Waypoint object — extract its .position
                if hasattr(mission_obj, 'active_waypoint') and mission_obj.active_waypoint:
                    target_wp = vec3_to_dict(mission_obj.active_waypoint.position)

                # For PlannedMission, queue is a WaypointQueue containing Waypoint objects
                if isinstance(mission_obj, PlannedMission) and hasattr(mission_obj, 'queue'):
                    path = [vec3_to_dict(wp.position) for wp in mission_obj.queue.queue]

            uavs_data.append({
                "id": drone.id,
                "readable_id": drone.readable_id,
                "position": vec3_to_dict(drone.state.position),
                "velocity": vec3_to_dict(drone.state.velocity),
                "heading": vec3_to_dict(drone.state.heading),
                "state": drone.state.current_state.value if isinstance(drone.state.current_state, DroneStateEnum) else str(drone.state.current_state),
                "mission": mission_name,
                "mission_status": mission_status,
                "target_waypoint": target_wp,
                "planned_path": path
            })
        return uavs_data

    @staticmethod
    def serialize_simulation_state(simulator, swarm_model) -> dict:
        return {
            "time": simulator.clock.sim_time,
            "paused": simulator.is_paused,
            "uavs": SimulationSerializer.serialize_uavs(swarm_model, swarm_model.mission_manager.active_assignments)
        }
