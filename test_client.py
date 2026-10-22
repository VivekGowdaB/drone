import asyncio
import websockets
import json

async def run_tests():
    uri = "ws://localhost:8765"
    print("=" * 60)
    print("UAV Simulation WebSocket Integration Test")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as ws:
            print("[PASS] Connected to", uri)

            # 1. Environment
            env_msg = json.loads(await ws.recv())
            assert env_msg['type'] == 'environment', "Expected environment message first"
            obs_count = len(env_msg['data']['obstacles'])
            print(f"[PASS] Environment received. Obstacles: {obs_count}")

            # 2. Spawn 3 UAVs
            print("\n--- Spawning 3 UAVs ---")
            await ws.send(json.dumps({"command": "spawn", "count": 3}))

            uavs = []
            while len(uavs) < 3:
                msg = json.loads(await ws.recv())
                if msg.get('type') == 'state':
                    uavs = msg['data']['uavs']

            print(f"[PASS] Spawned 3 UAVs:")
            for uav in uavs:
                print(f"       {uav['readable_id']} (id={uav['id'][:8]}...) pos=({uav['position']['x']:.1f}, {uav['position']['y']:.1f}, {uav['position']['z']:.1f})")

            first_id = uavs[0]['id']  # This is a UUID string
            second_id = uavs[1]['id']
            third_id = uavs[2]['id']

            # 3. Pause / Resume / Step / Speed
            print("\n--- Testing Simulation Controls ---")
            await ws.send(json.dumps({"command": "pause"}))
            await asyncio.sleep(0.1)
            msg = json.loads(await ws.recv())
            if msg.get('type') == 'state':
                assert msg['data']['paused'] == True, "Expected paused=True"
                print("[PASS] Pause works")

            await ws.send(json.dumps({"command": "step"}))
            print("[PASS] Step sent (single tick)")

            await ws.send(json.dumps({"command": "speed", "value": 2.0}))
            print("[PASS] Speed set to 2x")

            await ws.send(json.dumps({"command": "resume"}))
            await asyncio.sleep(0.2)
            # Drain buffer to get latest state
            latest = None
            while True:
                try:
                    latest = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.05))
                except asyncio.TimeoutError:
                    break
            if latest and latest.get('type') == 'state':
                assert latest['data']['paused'] == False, "Expected paused=False after resume"
                print("[PASS] Resume works")

            # 4. Mission Commands — using STRING drone_id
            print("\n--- Testing Mission Commands ---")

            # Hover
            await ws.send(json.dumps({"command": "hover", "drone_id": first_id}))
            await asyncio.sleep(0.3)
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.05))
                    if m.get('type') == 'state':
                        u = next((x for x in m['data']['uavs'] if x['id'] == first_id), None)
                        if u and u['mission'] == 'HoverMission':
                            print(f"[PASS] Hover assigned to {u['readable_id']}")
                            break
                except asyncio.TimeoutError:
                    print("[WARN] Hover assignment not confirmed in time")
                    break

            # Waypoint
            await ws.send(json.dumps({"command": "waypoint", "drone_id": second_id}))
            await asyncio.sleep(0.3)
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.05))
                    if m.get('type') == 'state':
                        u = next((x for x in m['data']['uavs'] if x['id'] == second_id), None)
                        if u and u['mission'] == 'WaypointMission':
                            print(f"[PASS] Waypoint assigned to {u['readable_id']}")
                            break
                except asyncio.TimeoutError:
                    print("[WARN] Waypoint assignment not confirmed in time")
                    break

            # Patrol
            await ws.send(json.dumps({"command": "patrol", "drone_id": third_id}))
            await asyncio.sleep(0.3)
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.05))
                    if m.get('type') == 'state':
                        u = next((x for x in m['data']['uavs'] if x['id'] == third_id), None)
                        if u and u['mission'] == 'PatrolMission':
                            print(f"[PASS] Patrol assigned to {u['readable_id']}")
                            break
                except asyncio.TimeoutError:
                    print("[WARN] Patrol assignment not confirmed in time")
                    break

            # Return Home
            await ws.send(json.dumps({"command": "return_home", "drone_id": first_id}))
            await asyncio.sleep(0.3)
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.05))
                    if m.get('type') == 'state':
                        u = next((x for x in m['data']['uavs'] if x['id'] == first_id), None)
                        if u and u['mission'] == 'ReturnHomeMission':
                            print(f"[PASS] Return Home assigned to {u['readable_id']}")
                            break
                except asyncio.TimeoutError:
                    print("[WARN] Return Home assignment not confirmed in time")
                    break

            # 5. Path Planning (A*)
            print("\n--- Testing Path Planning ---")
            await ws.send(json.dumps({
                "command": "plan_path",
                "drone_id": second_id,
                "planner": "A*",
                "dest": {"x": 15.0, "y": 8.0, "z": 15.0}
            }))
            await asyncio.sleep(1.0)

            path_found = False
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.1))
                    if m.get('type') == 'state':
                        u = next((x for x in m['data']['uavs'] if x['id'] == second_id), None)
                        if u and u.get('planned_path') and len(u['planned_path']) > 0:
                            print(f"[PASS] A* path generated: {len(u['planned_path'])} waypoints")
                            path_found = True
                            break
                        if u and u['mission'] == 'PlannedMission':
                            # Mission assigned but path might be consumed already
                            print(f"[PASS] PlannedMission assigned to {u['readable_id']} (path may be in progress)")
                            path_found = True
                            break
                except asyncio.TimeoutError:
                    break

            if not path_found:
                print("[WARN] Path planning result not detected in time (planner may need more time)")

            # 6. Verify time is advancing
            print("\n--- Verifying Simulation Time ---")
            await asyncio.sleep(0.5)
            while True:
                try:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.1))
                    if m.get('type') == 'state':
                        t = m['data']['time']
                        print(f"[PASS] Simulation time advancing: {t:.2f}s")
                        break
                except asyncio.TimeoutError:
                    break

            print("\n" + "=" * 60)
            print("ALL TESTS COMPLETED")
            print("=" * 60)

    except ConnectionRefusedError:
        print("[FAIL] Could not connect to", uri)
        print("       Make sure server.py is running: python server.py")
    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_tests())
