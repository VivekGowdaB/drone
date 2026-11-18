from sim.vec3 import Vec3
from config import WORLD_LIMIT, MIN_HEIGHT

# Human-readable names for the four square sectors (index 0..3).
SECTOR_NAMES = ["Sector Alpha", "Sector Bravo", "Sector Charlie", "Sector Delta"]


class Sector:
    """One square quarter of the operational map."""
    def __init__(self, sector_id, name, min_x, max_x, min_z, max_z):
        self.id = sector_id
        self.name = name
        self.min_x = min_x
        self.max_x = max_x
        self.min_z = min_z
        self.max_z = max_z
        self.on_hold = False

    def contains(self, x, z):
        return self.min_x <= x < self.max_x and self.min_z <= z < self.max_z

    @property
    def center(self):
        return (
            (self.min_x + self.max_x) / 2.0,
            MIN_HEIGHT,
            (self.min_z + self.max_z) / 2.0,
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bounds": {
                "min_x": self.min_x,
                "max_x": self.max_x,
                "min_z": self.min_z,
                "max_z": self.max_z,
            },
            "center": {
                "x": self.center[0],
                "y": self.center[1],
                "z": self.center[2],
            },
            "on_hold": self.on_hold,
        }


class ZoneManager:
    """Divides the map into four equal square sectors and tracks UAV
    ownership across sector boundaries.

    Pure backend subsystem: it owns no drone state of its own. It reads
    live positions from the SwarmModel, derives sector membership, and
    emits ENTER / LEAVE / HOLD / RELEASE events when a UAV crosses a
    boundary (handover). A sector flagged on-hold takes control of any
    UAV that enters it by forcing a hover in place.
    """
    def __init__(self, swarm_model):
        self.swarm_model = swarm_model
        limit = float(WORLD_LIMIT)
        specs = [
            # (min_x, max_x, min_z, max_z)
            (-limit, 0.0, -limit, 0.0),
            (0.0, limit, -limit, 0.0),
            (-limit, 0.0, 0.0, limit),
            (0.0, limit, 0.0, limit),
        ]
        self.sectors = [
            Sector(i, SECTOR_NAMES[i], *spec)
            for i, spec in enumerate(specs)
        ]
        # drone_id -> sector index currently owning the drone
        self.membership = {}
        # Ring buffer of zone events (ENTER/LEAVE/HOLD/RELEASE)
        self.events = []
        self._event_seq = 0

    def sector_for_position(self, x, z):
        """Return the sector index containing an XZ point, or None."""
        for sector in self.sectors:
            if sector.contains(x, z):
                return sector.id
        return None

    def get_sector(self, sector_id):
        for sector in self.sectors:
            if sector.id == sector_id:
                return sector
        return None

    def set_hold(self, sector_id, held):
        """Toggle sector control. Returns the number of UAVs affected."""
        sector = self.get_sector(sector_id)
        if sector is None:
            return 0
        sector.on_hold = bool(held)
        self._push_event(
            "HOLD" if held else "RELEASE", sector, None, None, None
        )
        if held:
            return self.enforce_hold()
        # Release: hover missions assigned by the hold simply complete in
        # place; the operator re-issues tasks for the freed UAVs.
        return 0

    def enforce_hold(self):
        """Force every UAV inside an on-hold sector to hover in place."""
        count = 0
        for drone in self.swarm_model.drones:
            sector_id = self.membership.get(drone.id)
            if sector_id is None:
                continue
            sector = self.get_sector(sector_id)
            if sector is not None and sector.on_hold:
                self.swarm_model.assign_hover(drone.id)
                count += 1
        return count

    def _push_event(self, event_type, sector, drone, from_sector, to_sector):
        self._event_seq += 1
        message = self._format_message(event_type, sector, drone, to_sector)
        self.events.append({
            "seq": self._event_seq,
            "time": round(self._current_time(), 2),
            "type": event_type,
            "sector_id": sector.id if sector is not None else None,
            "sector_name": sector.name if sector is not None else "",
            "drone_id": drone.id if drone is not None else None,
            "drone": drone.readable_id if drone is not None else "",
            "from_sector": from_sector.name if from_sector is not None else None,
            "to_sector": to_sector.name if to_sector is not None else None,
            "message": message,
        })
        # Keep the log bounded.
        if len(self.events) > 80:
            self.events = self.events[-80:]

    @staticmethod
    def _format_message(event_type, sector, drone, to_sector):
        name = drone.readable_id if drone is not None else ""
        if event_type == "LEAVE":
            return f"{name} left {sector.name}"
        if event_type == "ENTER":
            return f"{name} entered {sector.name} - {sector.name} now in control"
        if event_type == "HOLD":
            return f"{sector.name} placed on HOLD - incoming UAVs will hover"
        if event_type == "RELEASE":
            return f"{sector.name} released - full control resumed"
        return ""

    def _current_time(self):
        return getattr(self.swarm_model, "sim_time", 0.0)

    def update(self):
        """Detect sector transitions for every UAV and emit handover events."""
        current_ids = set()
        for drone in self.swarm_model.drones:
            current_ids.add(drone.id)
            pos = drone.state.position
            new_sector_id = self.sector_for_position(pos.x, pos.z)
            old_sector_id = self.membership.get(drone.id)
            self.membership[drone.id] = new_sector_id
            if old_sector_id == new_sector_id:
                continue
            # New UAV: report its entry only.
            if old_sector_id is None:
                if new_sector_id is not None:
                    self._push_event(
                        "ENTER",
                        self.get_sector(new_sector_id),
                        drone,
                        None,
                        None,
                    )
                continue
            old_sector = self.get_sector(old_sector_id)
            new_sector = self.get_sector(new_sector_id)
            # Emit LEAVE in the origin sector ...
            self._push_event("LEAVE", old_sector, drone, old_sector, new_sector)
            # ... and ENTER in the destination sector (handover).
            if new_sector is not None:
                self._push_event("ENTER", new_sector, drone, old_sector, new_sector)
                if new_sector.on_hold:
                    # The new sector takes control of the intruding UAV.
                    self.swarm_model.assign_hover(drone.id)
        # Drop stale memberships for removed drones.
        for stale_id in [
            d for d in self.membership if d not in current_ids
        ]:
            del self.membership[stale_id]

    def occupancy(self):
        """Return {sector_id: [drone_ids]} derived from live membership."""
        counts = {}
        for drone_id, sector_id in self.membership.items():
            counts.setdefault(sector_id, []).append(drone_id)
        return counts

    def to_dict(self):
        occupancy = self.occupancy()
        sectors = []
        for sector in self.sectors:
            data = sector.to_dict()
            data["drone_ids"] = occupancy.get(sector.id, [])
            data["drone_count"] = len(data["drone_ids"])
            sectors.append(data)
        return {"sectors": sectors, "events": list(self.events[-30:])}
