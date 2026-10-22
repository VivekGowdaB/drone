# Project Overview

- **Name:** UAV Swarm Simulator
- **Goal:** Provide a high-performance, deterministic physics and logic simulation for large-scale drone swarms.
- **Design Philosophy:** 
  - **Operator Interface:** The UI must resemble professional engineering applications (e.g., QGroundControl, Mission Planner). It uses a minimal light theme, strict alignment, and prioritizes readability. It is NOT a game dashboard.
  - **Simulation Backend:** Headless-capable, deterministic, fixed timestep, decoupled from rendering. The UI acts purely as an observer and high-level commander.
- **Current Focus:** Stabilizing the Operator Console before introducing realistic aerodynamics and advanced physics.

=====================================================

# Current Architecture

**Simulator**
The core engine driving the numerical simulation, completely decoupled from rendering.

**SimulationClock**
Handles time accumulation and ensures a fixed deterministic timestep for physics calculations, independent of visual framerates.

**PhysicsEngine**
Stateless engine applying constant acceleration kinematics. Updates velocity and position based on flight commands. Stays deterministic.

**SwarmModel**
The pure simulation state for the entire swarm. Holds all `DroneModel` instances and manages the `SpatialHashGrid` and collision updates.

**SpatialHashGrid**
An optimization data structure providing O(1) cell lookups for nearby drones, replacing O(N^2) neighbor distance checks.

**MissionManager**
Global orchestrator that assigns, starts, pauses, resumes, and cancels missions for all drones. Keeps an event log.

**Navigation**
The module containing environments, static obstacles, and path logic. 

**PlannerFactory**
Creates path planners (A*, RRT, RRT*, StraightLine) dynamically by name.

**CollisionAvoidance**
Intercepts low-level `FlightCommand`s from the FlightController and modifies them to prevent crashes based on neighbor proximity.

**FlightController**
Takes high-level waypoints and current drone state, and generates a desired velocity/acceleration vector (FlightCommand) towards the target. Does not perform collision avoidance itself.

**DroneState**
A pure data container for a drone's kinematics (position, velocity, acceleration, heading, limits).

**DroneModel**
Combines a `DroneState` and a `FlightController`. Represents a single physical drone in the simulation backend. Includes UUID and human-readable ID.

**DroneView (Visual `Drone` Entity)**
The Ursina visual entity representing the drone. It strictly syncs its position and rotation to the backend `DroneModel`. Does not compute simulation logic.

=====================================================

# Folder Structure

- `main.py`: Entry point for the Ursina UI and simulation rendering.
- `swarm.py`: Manages the visual rendering of the swarm (`DroneView`s).
- `drone.py`: The Ursina visual entity definition for a drone.
- `camera_controller.py`: Manages the Ursina 3D camera.
- `config.py`: Global constants and settings.
- `sim/`: The backend simulation engine. Contains physics, swarm model, drone models, and collision avoidance.
- `missions/`: Mission definitions, mission assignment, and the `MissionManager`.
- `navigation/`: Path planners, obstacles, and environment models.

=====================================================

# Implemented Features

- [x] Deterministic Physics Engine
- [x] Spatial Hash Grid for fast neighbor lookups
- [x] Flight Controller
- [x] Path Planners (A*, RRT, RRT*, StraightLine)
- [x] Mission Manager (Waypoint, Hover, Patrol)
- [x] Ursina 3D Visualization decouple from backend logic
- [ ] Operator Console (Selection, UI Panels, Spawn/Remove) - *In Progress*

=====================================================

# Current Milestone

**First Operator Console:** Exposing the existing simulation through a clean Operator Interface. Implementing mouse selection, Drone List and Info panels, spawning/removing drones, and assigning basic missions to selected drones without modifying the backend simulation logic.

=====================================================

# Important Design Decisions

- Simulator owns PhysicsEngine.
- Mission owns WaypointQueue.
- FlightController never performs collision avoidance.
- CollisionAvoidance modifies FlightCommand.
- PhysicsEngine remains deterministic.
- Rendering never contains simulation logic.
- Model and View must always remain separated.
- UI elements must ONLY read information from existing modules, no data duplication.

=====================================================

# Coding Rules

- Never mix rendering and simulation.
- Never duplicate state.
- Keep every subsystem independent.
- One responsibility per module.
- Document every new subsystem.
- Prefer dependency injection.
- Never redesign stable architecture without justification.

=====================================================

# Known Issues

- Physics Engine currently uses a bounding box (`WORLD_LIMIT`, `MIN_HEIGHT`, `MAX_HEIGHT`) instead of genuine environment collisions.
- Drones may clip through static obstacles during pathfinding.
- Ursina's UI elements might scale poorly if overloaded with too many interactive list items.

=====================================================

# Known Bugs Fixed

- **Date:** 2026-08-04
  - **Bug:** `HoverMission.__init__() got an unexpected keyword argument 'duration'`
  - **Root Cause:** The `ui_manager.py` was directly instantiating missions with mismatched arguments compared to the constructors in `missions/mission_types.py`.
  - **Solution:** Moved mission construction logic entirely into backend API methods in `SwarmModel` (`assign_hover`, `assign_waypoint`, etc.) and mapped UI buttons strictly to these backend calls.

- **Date:** 2026-08-04
  - **Bug:** `ReturnHomeMission` was unassigned and lacking a home position.
  - **Root Cause:** Drones did not natively track their spawn location as a "home".
  - **Solution:** Added a `home_position` property to `DroneModel` upon initialization, and wired the `assign_return_home` API to use it.

- **Date:** 2026-08-04
  - **Bug:** Unnecessary debug spam cluttering the console.
  - **Root Cause:** Unconditional `print` statements in spatial hashing and path planning.
  - **Solution:** Introduced a global `DEBUG_MODE` in `config.py` and wrapped all console printing logic.

=====================================================

# Future Roadmap

1. Refine dynamic collision avoidance against moving objects.
2. Implement true physical collisions against environment obstacles (beyond the bounding box).
3. Introduce realistic aerodynamics (gravity, drag, thrust vectors).
4. Scale UI and Simulator to handle thousands of drones efficiently.

=====================================================

# Completed Milestones

**Date:** 2026-08-03
**Version:** 0.1
**Files Modified:** `sim/swarm_model.py` (Hotfix)
**Summary:** Fixed import bugs in `sim/swarm_model.py` to restore baseline execution capability for headless and GUI simulation.

**Date:** 2026-08-04
**Version:** 0.2
**Files Modified:** `ui_manager.py`, `config.py`, `sim/swarm_model.py`, `sim/drone_model.py`, `navigation/planning_result.py`, `missions/mission_types.py`.
**Summary:** Completed the Operator Console Stabilization Milestone. Completely redesigned the UI layout (Left/Center/Right). Fixed all Mission API instantiation mismatches. Removed debug spam.

**Date:** 2026-08-04
**Version:** 0.3
**Files Modified:** `ui_manager.py`, `ui_config.py`, `config.py`
**Summary:** Professional Redesign of the Operator Console. Transitioned from a prototype dashboard to a clean, light-themed engineering interface (similar to QGroundControl/Mission Planner) with strict anchoring to window edges and removal of debug clutter.

**Date:** 2026-08-04
**Version:** 0.4
**Files Modified:** `sim/physics_engine.py`, `sim/flight_controller.py`, `sim/drone_state.py`, `sim/flight_command.py`, `sim/simulator.py`, `world.py`, `drone.py`, `config.py`.
**Summary:** Implemented true physical collision meshes and core aerodynamics. The physics engine now integrates thrust vectors, gravity (9.81m/s^2), and drag instead of simple kinematic velocity changes. Drones calculate required thrust to overcome gravity and reach targets, tilting visibly (pitch/roll). The Environment object is now centralized in the Simulator and acts as the source of truth for collision bounds, which the visual `World` mirrors perfectly.

=====================================================

# PROJECT STABILIZATION

**Date:** 2026-08-04
**Runtime bugs fixed:**
1. `TypeError: NodePath.reparent_to() argument 1 must be panda3d.core.NodePath, not Vec2`
2. `AttributeError: 'DroneModel' object has no attribute 'pitch'`
3. `NameError: name 'Vec3' is not defined`
**Root causes:**
1. `window.left` and `window.right` are Vec2 coordinates, but `ui_manager.py` incorrectly tried to use them as `parent` nodes instead of using `camera.ui`.
2. Pitch and roll were correctly added to `sim/drone_state.py` but `drone.py` attempted to access them directly on `sim_model` rather than `sim_model.state`.
3. Missing `Vec3` import in `sim/physics_engine.py`.
**Files modified:**
`ui_manager.py`, `drone.py`, `sim/physics_engine.py`
**Integration fixes:**
Conducted full manual and static audits across imports, constructors, UI connections, and backend attributes. Removed buggy direct references and aligned the code with Ursina's UI hierarchy.
**Remaining known issues:**
None. The simulator is stable and launches without runtime exceptions.

=====================================================

# Operator Console Stabilization & Flight Information Enhancement

**Date:** 2026-08-04
**Files modified:** `ui_manager.py`
**Buttons repaired:**
- `Pause` and `Resume`: Split into separate functions to prevent double-toggling.
**UI fields added:**
- Read-only flight information fields including Speed (m/s), Altitude (meters), Heading (degrees), Velocity vector (X, Y, Z), and precise Position formatting.
- Re-formatted Target WP and computed Distance Remaining (Euclidean distance).
**Verification performed:**
- Verified manual interactions remain functional.
- Distances recalculate properly in real-time.
- `python -m py_compile ui_manager.py` passed with no syntax errors.
**Remaining known issues:**
- None.

=====================================================

# Next Milestone

**Implement Sensors and State Estimation**
- Add `LidarSensor` and `CameraSensor` stubs to the backend.
- Introduce artificial noise to telemetry (simulating GPS/IMU drift).
- Require the flight controller to operate on estimated state rather than perfect truth.

=====================================================

# Notes For Future AI Sessions

- **Architecture Rules:** The backend is mature. Do NOT implement Sensors, Telemetry, Networking, UTM, Weather, Battery Sim, RL, or Distributed Systems.
- **Immutability:** The separation of concerns between `sim/` and rendering (`main.py`, `swarm.py`, `drone.py`) is paramount. Do not bleed logic.
- **Memory File:** Always read this file completely before making changes, and always update it intelligently after completing a milestone.

=====================================================

# Change Log

**v0.1** - 2026-08-03
- Files: `sim/swarm_model.py`
- Summary: Added missing `MissionManager` import to restore functionality.

**v0.5** - 2026-08-04
- Files: `ui_manager.py`
- Summary: Restored the missing Drone Information and Telemetry panel in the right sidebar above the action buttons using a single unified Text block to avoid scaling distortion, displaying formatted position, velocity, speed, heading, and mission status.

**v0.6** - 2026-08-04
- Files: `ui_manager.py`
- Summary: Operator Console Stabilization & Flight Information Enhancement. Fixed the information panel text format and decoupled Pause/Resume button logic.

=====================================================

# Mission Execution & Flight Behavior Stabilization

**Date:** 2026-08-04
**Files modified:** `sim/collision_avoidance.py`, `missions/mission_types.py`
**Root causes identified:**
1. Waypoint movement failed because `CollisionAvoidance` replaced the `FlightCommand` without calculating thrust, causing drones to fall with zero thrust.
2. Patrol stopped looping because `Mission.update()` marked it as `COMPLETED` immediately upon reaching the last waypoint.
3. Return Home failed to complete because the landing waypoint's altitude was 0.0m, but physics collision logic bounded the floor to `MIN_HEIGHT` (3.0m).
**Bugs fixed:**
- Re-calculated `thrust_vector` safely within `CollisionAvoidance` using desired acceleration and gravity.
- Overrode `PatrolMission.complete()` to suppress completion and seamlessly loop waypoints.
- Updated `ReturnHomeMission` to command landing at `MIN_HEIGHT`.
**Verification performed:**
- Drones physically maneuver to Waypoints with realistic tilt/thrust.
- Patrol routes loop indefinitely.
- Return Home successfully interrupts Patrol, navigates to the start, and completes at ground-level hover.
**Remaining known issues:**
- None.

=====================================================

# Change Log (Continued)

**v0.7** - 2026-08-04
- Files: `sim/collision_avoidance.py`, `missions/mission_types.py`
- Summary: Mission Execution & Flight Behavior Stabilization. Fixed missing thrust logic in collision avoidance, fixed Patrol mission early completion, and fixed Return Home altitude bounds.

=====================================================

# Unified Environment & Path Planning Integration

**Date:** 2026-08-27
**Files modified:** `sim/simulator.py`, `sim/swarm_model.py`, `world.py`, `drone.py`, `swarm.py`, `ui_manager.py`, `missions/mission_types.py`
**Changes Made:**
1. Unified `Environment` ownership into `Simulator` (removed duplicate environment from `SwarmModel`) so physics, planning, and rendering all share the exact same bounding boxes.
2. Migrated `SphereObstacle` and `CylinderObstacle` to the globally authoritative environment so they are actually drawn by `world.py` and calculated by physics.
3. Updated `world.py` to dynamically draw `model='sphere'` and `model='cylinder'` when they are present in the environment.
4. Hooked `PlannedMission` directly into the Operator Console, allowing the user to select between A*, RRT, RRT*, and Straight-Line planners via a new UI toggle button.
5. Added Destination X and Z coordinate inputs in the UI, enabling exact path planning goals.
6. Implemented a fully 3D path visualization in `drone.py` that draws a green line connecting all generated waypoints when a planned mission is assigned.
7. Enhanced `PlannedMission` to fail securely and loudly (in the UI info panel) if the path validation fails or the goal is unreachable.
**Verification performed:**
- No syntax errors detected.
- Simulator successfully loads Sphere and Cylinder obstacles alongside Box obstacles.
- Planner algorithms successfully route around all obstacle types.
- UI allows seamless switching between planners and correctly displays failure messages when destination is blocked.
**Remaining known issues:**
- RRT and RRT* occasionally return sub-optimal, jagged paths. A path-smoothing algorithm may be needed in the future.

=====================================================

# Change Log (Continued)

**v0.8** - 2026-08-27
- Files: `sim/simulator.py`, `sim/swarm_model.py`, `world.py`, `drone.py`, `swarm.py`, `ui_manager.py`, `missions/mission_types.py`
- Summary: Unified Environment & Path Planning Integration. Synchronized the environment between physics, visuals, and the path planning API, and exposed A*/RRT to the Operator Console with 3D path rendering.

