import asyncio
import websockets
import json
import threading
import time
from sim.vec3 import Vec3
from sim.simulator import Simulator
from sim.serializer import SimulationSerializer

class SimulationServer:
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.simulator = Simulator(target_hz=60)
        self.running = True

        # Keep the latest serialized state to broadcast
        self.latest_dynamic_state = {}
        self.clients = set()

        # Start simulation thread (completely independent of asyncio and WebSockets)
        self.sim_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.sim_thread.start()

    def simulation_loop(self):
        """Runs the fixed timestep simulation independently of everything else."""
        last_time = time.time()
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # Step the simulation mathematically
            self.simulator.tick(dt)

            # Serialize the state
            try:
                self.latest_dynamic_state = SimulationSerializer.serialize_simulation_state(
                    self.simulator, self.simulator.swarm_model
                )
            except Exception as e:
                print(f"Serialization error: {e}")

            # Prevent 100% CPU usage
            time.sleep(0.005)

    async def broadcast_loop(self):
        """Broadcasts dynamic state to all clients at 30Hz."""
        while self.running:
            if self.clients and self.latest_dynamic_state:
                message = json.dumps({"type": "state", "data": self.latest_dynamic_state})
                disconnected = set()
                for client in list(self.clients):
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.add(client)

                # Cleanup disconnected clients
                if disconnected:
                    self.clients -= disconnected

            # Broadcast at roughly 30Hz
            await asyncio.sleep(1/30.0)

    def handle_command(self, payload):
        """Validates and processes commands from the frontend."""
        try:
            cmd = payload.get("command")
            if not cmd:
                return

            # Basic sim controls
            if cmd == "pause":
                self.simulator.pause()
            elif cmd == "resume":
                self.simulator.resume()
            elif cmd == "step":
                self.simulator.step()
            elif cmd == "speed":
                val = float(payload.get("value", 1.0))
                self.simulator.set_speed(val)

            # Drone controls
            elif cmd == "spawn":
                count = int(payload.get("count", 1))
                self.simulator.swarm_model.spawn_drones(count)
            elif cmd == "hover":
                drone_id = payload.get("drone_id")
                if drone_id:
                    self.simulator.swarm_model.assign_hover(drone_id)
            elif cmd == "waypoint":
                drone_id = payload.get("drone_id")
                if drone_id:
                    self.simulator.swarm_model.assign_waypoint(drone_id)
            elif cmd == "patrol":
                drone_id = payload.get("drone_id")
                if drone_id:
                    self.simulator.swarm_model.assign_patrol(drone_id)
            elif cmd == "return_home":
                drone_id = payload.get("drone_id")
                if drone_id:
                    self.simulator.swarm_model.assign_return_home(drone_id)
            elif cmd == "plan_path":
                drone_id = payload.get("drone_id")
                dest = payload.get("dest")
                planner = payload.get("planner", "A*")
                if drone_id and dest:
                    target_vec = Vec3(float(dest["x"]), float(dest["y"]), float(dest["z"]))
                    self.simulator.swarm_model.assign_planned_mission(drone_id, planner, target_vec)

        except Exception as e:
            print(f"Command error: {e}")

    async def handler(self, websocket):
        """Handles a single client connection."""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

        try:
            # Send initial environment state ONCE on connect
            env_data = SimulationSerializer.serialize_environment(self.simulator.environment)
            await websocket.send(json.dumps({"type": "environment", "data": env_data}))

            # Listen for commands
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    self.handle_command(payload)
                except json.JSONDecodeError:
                    print("Invalid JSON received from client")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def start_server(self):
        # Start broadcast task
        asyncio.create_task(self.broadcast_loop())

        # Start websocket server
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"WebSocket server listening on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

if __name__ == "__main__":
    server = SimulationServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        server.running = False
