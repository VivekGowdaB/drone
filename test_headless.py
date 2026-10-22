from sim.simulator import Simulator
import time

def run_headless():
    sim = Simulator(target_hz=60)
    print("Starting headless simulation...")
    sim.swarm_model.spawn_drones(1)
    
    # Run 120 ticks (2 seconds of sim time)
    for _ in range(120):
        sim.step()
        
    print(f"Simulation time: {sim.clock.sim_time:.2f}s")
    print(f"Number of drones: {len(sim.swarm_model.drones)}")
    print(f"Position of drone 0: {sim.swarm_model.drones[0].position}")
    print("Headless simulation successful.")

if __name__ == "__main__":
    run_headless()
