from missions.waypoint import Waypoint
from enum import Enum
from missions.waypoint_queue import WaypointQueue
from missions.mission_events import MissionEvent, MissionEventType
import uuid

class MissionStatus(Enum):
    CREATED = "Created"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"

class Mission:
    """Abstract base class for all missions."""
    def __init__(self):
        self.mission_id = str(uuid.uuid4())
        self.status = MissionStatus.CREATED
        self.queue = WaypointQueue()
        self.drone_id = None 
        
        # State tracking for the active waypoint
        self.active_waypoint = None
        self.hold_timer = 0.0
        
        # Event callbacks
        self.on_event = None

    def _emit_event(self, event_type: MissionEventType, data=None):
        if self.on_event:
            self.on_event(MissionEvent(event_type, self.mission_id, self.drone_id, data))

    def initialize(self, drone_id: str, on_event_callback=None):
        self.drone_id = drone_id
        self.on_event = on_event_callback
        self.status = MissionStatus.CREATED
        self.hold_timer = 0.0

    def start(self):
        if self.status in [MissionStatus.CREATED, MissionStatus.PAUSED]:
            self.status = MissionStatus.RUNNING
            self.active_waypoint = self.queue.peek_next()
            self._emit_event(MissionEventType.MISSION_STARTED)

    def pause(self):
        if self.status == MissionStatus.RUNNING:
            self.status = MissionStatus.PAUSED
            self._emit_event(MissionEventType.MISSION_PAUSED)

    def resume(self):
        if self.status == MissionStatus.PAUSED:
            self.status = MissionStatus.RUNNING
            self._emit_event(MissionEventType.MISSION_RESUMED)

    def cancel(self):
        self.status = MissionStatus.CANCELLED
        self.queue.clear()
        self.active_waypoint = None
        self._emit_event(MissionEventType.MISSION_CANCELLED)

    def complete(self):
        self.status = MissionStatus.COMPLETED
        self.active_waypoint = None
        self._emit_event(MissionEventType.MISSION_COMPLETED)

    def update(self, dt: float, drone_position) -> 'Waypoint':
        """Called every tick by MissionManager. Returns the active waypoint."""
        if self.status != MissionStatus.RUNNING:
            return None
            
        if not self.active_waypoint:
            self.complete()
            return None
            
        # Check if waypoint reached
        dist = (drone_position - self.active_waypoint.position).length()
        if dist <= self.active_waypoint.acceptance_radius:
            # We are within the acceptance radius, check hold time
            self.hold_timer += dt
            if self.hold_timer >= self.active_waypoint.hold_time:
                self._emit_event(MissionEventType.WAYPOINT_REACHED, {"waypoint_id": self.active_waypoint.id})
                
                # Advance
                self.queue.advance()
                self.active_waypoint = self.queue.peek_next()
                self.hold_timer = 0.0
                
                if not self.active_waypoint:
                    self.complete()
                    
        return self.active_waypoint
