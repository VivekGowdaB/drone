import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, Sky, Html, Line } from '@react-three/drei';
import './App.css';

// --- WebSocket Connection Hook ---
function useSimulationSocket(url) {
  const [environment, setEnvironment] = useState({ obstacles: [] });
  const [simState, setSimState] = useState({ uavs: [], time: 0, paused: false, zones: { sectors: [], events: [] } });
  const [status, setStatus] = useState("Disconnected");
  const [zoneEvents, setZoneEvents] = useState([]);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const connect = () => {
      if (!mountedRef.current) return;

      setStatus("Connecting...");

      let ws;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        console.error("WebSocket creation failed:", err);
        setStatus("Disconnected");
        reconnectRef.current = setTimeout(connect, 2000);
        return;
      }

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        console.log("WebSocket connected");
        setStatus("Connected");
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'environment') {
            setEnvironment(msg.data);
          } else if (msg.type === 'state') {
            setSimState(msg.data);
            // Accumulate sector enter/leave events locally so the log
            // survives reconnects and backend buffer trimming.
            const evts = msg.data.zones && msg.data.zones.events;
            if (evts && evts.length) {
              setZoneEvents(prev => {
                const merged = [...prev, ...evts];
                const seen = new Set();
                const deduped = [];
                for (let i = merged.length - 1; i >= 0; i--) {
                  if (!seen.has(merged[i].seq)) {
                    seen.add(merged[i].seq);
                    deduped.push(merged[i]);
                  }
                }
                return deduped.reverse().slice(-100);
              });
            }
          }
        } catch (e) {
          console.error("Failed to parse message:", e);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        console.log("WebSocket closed, reconnecting in 2s...");
        setStatus("Disconnected");
        reconnectRef.current = setTimeout(connect, 2000);
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url]);

  const sendCommand = useCallback((cmdObj) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify(cmdObj);
      console.log("Sending command:", payload);
      ws.send(payload);
    } else {
      console.warn("Cannot send command, WebSocket not connected. State:", ws?.readyState);
    }
  }, []);

  return { environment, simState, status, sendCommand, zoneEvents };
}


// --- 3D RENDERERS ---

function EnvironmentRenderer({ obstacles }) {
  if (!obstacles || obstacles.length === 0) return null;

  return (
    <group>
      {obstacles.map((obs, idx) => {
        if (obs.type === 'box') {
          return (
            <mesh key={`obs-${idx}`} position={[obs.center.x, obs.center.y, obs.center.z]} castShadow receiveShadow>
              <boxGeometry args={[obs.size.x, obs.size.y, obs.size.z]} />
              <meshStandardMaterial color={obs.size.y > 10 ? "#7a6b5d" : "#999999"} transparent opacity={0.85} />
            </mesh>
          );
        }
        if (obs.type === 'sphere') {
          return (
            <mesh key={`obs-${idx}`} position={[obs.center.x, obs.center.y, obs.center.z]} castShadow receiveShadow>
              <sphereGeometry args={[obs.radius, 32, 32]} />
              <meshStandardMaterial color="#bb8855" transparent opacity={0.7} />
            </mesh>
          );
        }
        if (obs.type === 'cylinder') {
          return (
            <mesh key={`obs-${idx}`} position={[obs.center_base.x, obs.center_base.y + obs.height / 2, obs.center_base.z]} castShadow receiveShadow>
              <cylinderGeometry args={[obs.radius, obs.radius, obs.height, 32]} />
              <meshStandardMaterial color="#888888" transparent opacity={0.8} />
            </mesh>
          );
        }
        return null;
      })}
    </group>
  );
}

function UAVMesh({ uav, isSelected, onSelect, held }) {
  const pathPoints = uav.planned_path && uav.planned_path.length > 1
    ? uav.planned_path.map(p => [p.x, p.y, p.z])
    : null;

  const bodyColor = held ? "#ffaa00" : (isSelected ? "#00ff88" : "#ff4444");

  return (
    <group>
      {/* UAV body */}
      <mesh
        position={[uav.position.x, uav.position.y, uav.position.z]}
        castShadow
        onClick={(e) => { e.stopPropagation(); onSelect(uav.id); }}
      >
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshStandardMaterial
          color={bodyColor}
          emissive={bodyColor}
          emissiveIntensity={isSelected ? 0.4 : 0.15}
        />

        {/* Label */}
        <Html position={[0, 1.0, 0]} center style={{ pointerEvents: 'none' }}>
          <div style={{
            background: isSelected ? 'rgba(0,255,136,0.85)' : 'rgba(0,0,0,0.75)',
            color: isSelected ? '#000' : '#fff',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            whiteSpace: 'nowrap',
            fontWeight: isSelected ? 'bold' : 'normal',
            border: isSelected ? '1px solid #00ff88' : 'none'
          }}>
            {uav.readable_id || uav.id.substring(0, 8)} [{uav.state}]
          </div>
        </Html>
      </mesh>

      {/* Planned Path Line */}
      {pathPoints && (
        <Line
          points={pathPoints}
          color="#00ff00"
          lineWidth={2}
          dashed={false}
        />
      )}

      {/* Target Waypoint Marker */}
      {uav.target_waypoint && (
        <mesh position={[uav.target_waypoint.x, uav.target_waypoint.y, uav.target_waypoint.z]}>
          <sphereGeometry args={[0.25, 8, 8]} />
          <meshBasicMaterial color="#ffff00" />
        </mesh>
      )}
    </group>
  );
}

function SwarmRenderer({ uavs, selectedUAV, onSelectUAV, sectors }) {
  if (!uavs || uavs.length === 0) return null;

  const heldSet = new Set((sectors || []).filter(s => s.on_hold).map(s => s.id));

  return (
    <group>
      {uavs.map((uav) => (
        <UAVMesh
          key={uav.id}
          uav={uav}
          isSelected={selectedUAV === uav.id}
          onSelect={onSelectUAV}
          held={uav.sector != null && heldSet.has(uav.sector)}
        />
      ))}
    </group>
  );
}

const SECTOR_TINTS = ["#3d7bd9", "#4caf7d", "#d98a3d", "#b3599f"];

function SectorOverlays({ sectors, selectedSector, onSelectSector }) {
  if (!sectors || sectors.length === 0) return null;

  return (
    <group>
      {sectors.map((s, i) => {
        const w = s.bounds.max_x - s.bounds.min_x;
        const h = s.bounds.max_z - s.bounds.min_z;
        const cx = (s.bounds.min_x + s.bounds.max_x) / 2;
        const cz = (s.bounds.min_z + s.bounds.max_z) / 2;
        const isSelected = selectedSector === s.id;
        return (
          <group key={s.id}>
            <mesh
              rotation={[-Math.PI / 2, 0, 0]}
              position={[cx, 0.02, cz]}
              onClick={(e) => { e.stopPropagation(); onSelectSector(s.id); }}
              onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer'; }}
              onPointerOut={() => { document.body.style.cursor = 'default'; }}
            >
              <planeGeometry args={[w, h]} />
              <meshBasicMaterial
                color={isSelected ? "#00d4aa" : SECTOR_TINTS[i % SECTOR_TINTS.length]}
                transparent
                opacity={isSelected ? 0.22 : 0.07}
                depthWrite={false}
              />
            </mesh>
            <Html position={[cx, 1.5, cz]} center style={{ pointerEvents: 'none' }}>
              <div style={{
                background: s.on_hold ? 'rgba(255,170,0,0.85)' : 'rgba(0,0,0,0.6)',
                color: s.on_hold ? '#000' : '#fff',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                whiteSpace: 'nowrap',
                fontWeight: isSelected ? 'bold' : 'normal',
                border: isSelected ? '1px solid #00d4aa' : 'none'
              }}>
                {s.name} · {s.drone_count} UAV{s.on_hold ? ' · HOLD' : ''}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

function CADTarget({ position, color, isGhost }) {
  if (!position) return null;
  const { x, y, z } = position;
  return (
    <group position={[x, y, z]}>
      <mesh>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial color={color} transparent={isGhost} opacity={isGhost ? 0.6 : 1} depthTest={false} />
      </mesh>
      <Line points={[[0, 0, 0], [0, -y, 0]]} color={color} transparent={isGhost} opacity={isGhost ? 0.6 : 1} lineWidth={2} depthTest={false} />
      <Line points={[[0, -y, 0], [-x, -y, 0]]} color="#ff4444" transparent={isGhost} opacity={isGhost ? 0.6 : 1} lineWidth={2} depthTest={false} />
      <Line points={[[0, -y, 0], [0, -y, -z]]} color="#44aaff" transparent={isGhost} opacity={isGhost ? 0.6 : 1} lineWidth={2} depthTest={false} />
    </group>
  );
}

function SimulationScene({ environment, simState, selectedUAV, selectedUAVData, onSelectUAV, isSelectingDestination, setSelectedDestination, selectedDestination, hoveredDestination, setHoveredDestination, currentAltitude, setCurrentAltitude, sectors, selectedSector, onSelectSector }) {
  const zoneData = simState.zones || { sectors: [], events: [] };
  return (
    <Canvas camera={{ position: [0, 25, 40], fov: 55 }}>
      <Sky distance={450000} sunPosition={[5, 1, 3]} inclination={0} azimuth={0.25} />
      <ambientLight intensity={0.45} />
      <directionalLight position={[15, 25, 15]} intensity={1.2} castShadow />
      <directionalLight position={[-10, 15, -5]} intensity={0.3} />

      <Grid
        position={[0, -0.01, 0]}
        args={[100, 100]}
        cellSize={2}
        cellThickness={0.4}
        cellColor="#555555"
        sectionSize={10}
        sectionThickness={1}
        sectionColor="#884444"
        fadeDistance={60}
        fadeStrength={1}
      />

      {isSelectingDestination && !selectedDestination && (
        <mesh
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, currentAltitude, 0]}
          onPointerMove={(e) => {
            e.stopPropagation();
            setHoveredDestination({ x: e.point.x, y: currentAltitude, z: e.point.z });
          }}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedDestination({ x: e.point.x, y: currentAltitude, z: e.point.z });
            setHoveredDestination(null);
          }}
          onWheel={(e) => {
            e.stopPropagation();
            // Scroll to change altitude
            setCurrentAltitude(prev => Math.max(0, prev - e.deltaY * 0.01));
          }}
        >
          <planeGeometry args={[2000, 2000]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      )}

      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.02, 0]}
        receiveShadow
      >
        <planeGeometry args={[200, 200]} />
        <meshStandardMaterial color="#2d3b2d" />
      </mesh>

      <CADTarget position={hoveredDestination} color="#00ffff" isGhost={true} />
      <CADTarget position={selectedDestination} color="#ff00ff" isGhost={false} />

      <SectorOverlays
        sectors={zoneData.sectors}
        selectedSector={selectedSector}
        onSelectSector={onSelectSector}
      />

      <EnvironmentRenderer obstacles={environment.obstacles} />
      <SwarmRenderer
        uavs={simState.uavs}
        selectedUAV={selectedUAV}
        onSelectUAV={onSelectUAV}
        sectors={zoneData.sectors}
      />

      <OrbitControls makeDefault enabled={!isSelectingDestination} />
    </Canvas>
  );
}


// --- UI LAYOUT ---

function TopBar({ paused, sendCommand, connected }) {
  return (
    <div className="panel top-bar">
      <h2>UAV Simulation Operator Console</h2>
      <div className="controls">
        <button
          className={!paused && connected ? "btn-active" : ""}
          onClick={() => sendCommand({command: 'resume'})}
          disabled={!connected}
        >
          ▶ Play
        </button>
        <button
          className={paused && connected ? "btn-active" : ""}
          onClick={() => sendCommand({command: 'pause'})}
          disabled={!connected}
        >
          ⏸ Pause
        </button>
        <button
          onClick={() => sendCommand({command: 'step'})}
          disabled={!connected}
        >
          ⏭ Step
        </button>
        <label className="speed-label">
          Speed:
          <select
            defaultValue="1"
            onChange={(e) => sendCommand({command: 'speed', value: parseFloat(e.target.value)})}
            disabled={!connected}
          >
            <option value="0.25">0.25x</option>
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
            <option value="10">10x</option>
          </select>
        </label>
      </div>
    </div>
  );
}

function LeftPanel({ environment, connected, uavs, selectedUAV, onSelectUAV, sendCommand, sectors, selectedSector, onSelectSector, zoneEvents }) {
  const [spawnCount, setSpawnCount] = useState(3);

  const activeSector = sectors ? sectors.find(s => s.id === selectedSector) : null;
  const visibleUavs = selectedSector == null
    ? uavs
    : (uavs || []).filter(u => u.sector === selectedSector);

  const sectorEvents = selectedSector == null
    ? zoneEvents
    : (zoneEvents || []).filter(e => e.sector_id === selectedSector);

  return (
    <div className="panel left-panel">
      <h3>Environment</h3>
      <div className="panel-section">
        <p>Obstacles: {environment.obstacles ? environment.obstacles.length : 0}</p>
      </div>

      <h3>Map Sectors {selectedSector != null ? `(${activeSector ? activeSector.name : ''})` : ''}</h3>
      <div className="panel-section sector-grid">
        {sectors && sectors.map(s => (
          <div
            key={s.id}
            className={`sector-card ${selectedSector === s.id ? 'selected' : ''} ${s.on_hold ? 'on-hold' : ''}`}
            onClick={() => onSelectSector(selectedSector === s.id ? null : s.id)}
          >
            <div className="sector-card-top">
              <span className="sector-name">{s.name}</span>
              <span className="sector-count">{s.drone_count}</span>
            </div>
            <div className="sector-card-bottom">
              <span className={`sector-state ${s.on_hold ? 'hold' : ''}`}>
                {s.on_hold ? 'ON HOLD' : 'ACTIVE'}
              </span>
              <button
                className="sector-hold-btn"
                disabled={!connected}
                onClick={(e) => {
                  e.stopPropagation();
                  sendCommand(s.on_hold
                    ? { command: 'sector_release', sector_id: s.id }
                    : { command: 'sector_hold', sector_id: s.id });
                }}
              >
                {s.on_hold ? 'Release' : 'Hold'}
              </button>
            </div>
          </div>
        ))}
        {selectedSector != null && (
          <button
            className="full-btn clear-sector-btn"
            onClick={() => onSelectSector(null)}
          >
            Show All Sectors
          </button>
        )}
      </div>

      <h3>Manage UAVs</h3>
      <div className="panel-section">
        <div className="spawn-row">
          <input
            type="number"
            value={spawnCount}
            onChange={(e) => setSpawnCount(parseInt(e.target.value, 10) || 1)}
            disabled={!connected}
            min="1"
            max="50"
            style={{ width: '60px' }}
          />
          <button
            className="full-btn"
            disabled={!connected}
            onClick={() => sendCommand({command: 'spawn', count: spawnCount})}
          >
            Add
          </button>
          <button
            className="full-btn clear-all-btn"
            disabled={!connected || !uavs || uavs.length === 0}
            onClick={() => sendCommand({command: 'remove_all'})}
            title="Remove all UAVs"
          >
            Remove All
          </button>
        </div>
      </div>

      <h3>
        Drone List ({visibleUavs ? visibleUavs.length : 0})
        {selectedSector != null && activeSector ? ` — ${activeSector.name}` : ''}
      </h3>
      <div className="panel-section drone-list-scroll">
        {visibleUavs && visibleUavs.map(uav => (
          <div
            key={uav.id}
            className={`uav-item ${selectedUAV === uav.id ? 'selected' : ''}`}
            onClick={() => onSelectUAV(uav.id)}
          >
            <span className="uav-name">{uav.readable_id || uav.id.substring(0, 8)}</span>
            <span className="uav-item-right">
              <span className="uav-mission">{uav.mission}</span>
              <button
                className="uav-remove-btn"
                title="Remove this UAV"
                disabled={!connected}
                onClick={(e) => {
                  e.stopPropagation();
                  sendCommand({ command: 'remove', drone_id: uav.id });
                }}
              >
                ✕
              </button>
            </span>
          </div>
        ))}
        {(!visibleUavs || visibleUavs.length === 0) && (
          <p className="empty-msg">
            {selectedSector != null ? 'No UAVs in this sector.' : 'No UAVs. Click Spawn to add.'}
          </p>
        )}
      </div>

      <h3>Sector Events {selectedSector != null && activeSector ? `— ${activeSector.name}` : '(All)'}</h3>
      <div className="panel-section event-log-scroll">
        {sectorEvents && sectorEvents.map(e => (
          <div key={e.seq} className={`event-row event-${e.type.toLowerCase()}`}>
            <span className="event-time">{e.time.toFixed(0)}s</span>
            <span className="event-msg">{e.message}</span>
          </div>
        ))}
        {(!sectorEvents || sectorEvents.length === 0) && (
          <p className="empty-msg">No sector transitions yet.</p>
        )}
      </div>
    </div>
  );
}

function RightPanel({ selectedUAVData, selectedUAV, connected, sendCommand, isSelectingDestination, setIsSelectingDestination, selectedDestination, setSelectedDestination, hoveredDestination, sectors, selectedSector }) {
  const [planner, setPlanner] = useState("A*");

  const activeSector = sectors ? sectors.find(s => s.id === selectedSector) : null;
  const droneSector = sectors && selectedUAVData && selectedUAVData.sector != null
    ? sectors.find(s => s.id === selectedUAVData.sector)
    : null;

  // Actions only apply to a drone that belongs to the focused sector.
  const noSelection = !selectedUAV ||
    (selectedSector != null && selectedUAVData && selectedUAVData.sector !== selectedSector);
  // A sector on HOLD refuses new task assignments.
  const sectorHeld = activeSector ? activeSector.on_hold : false;
  const actionsDisabled = !connected || noSelection || sectorHeld;
  const displayDest = selectedDestination || hoveredDestination;

  return (
    <div className="panel right-panel">
      {/* Active sector context */}
      {selectedSector != null && (
        <div className={`sector-banner ${sectorHeld ? 'held' : ''}`}>
          <div className="sector-banner-title">
            Control Focus: {activeSector ? activeSector.name : `Sector ${selectedSector}`}
          </div>
          {sectorHeld && (
            <div className="sector-banner-sub">
              Sector is ON HOLD — UAVs hover, new tasks blocked
            </div>
          )}
        </div>
      )}

      {/* Telemetry */}
      <h3>Drone Information</h3>
      <div className="panel-section telemetry">
        {selectedUAVData ? (
          <>
            <div className="telem-row"><span>ID:</span><span>{selectedUAVData.readable_id}</span></div>
            <div className="telem-row"><span>In Sector:</span><span>{droneSector ? droneSector.name : 'Outside'}</span></div>
            <div className="telem-row"><span>State:</span><span>{selectedUAVData.state}</span></div>
            <div className="telem-row"><span>Mission:</span><span>{selectedUAVData.mission}</span></div>
            <div className="telem-row"><span>Status:</span><span>{selectedUAVData.mission_status}</span></div>
            <hr/>
            <div className="telem-row">
              <span>Position:</span>
              <span>
                ({selectedUAVData.position.x.toFixed(1)},
                {selectedUAVData.position.y.toFixed(1)},
                {selectedUAVData.position.z.toFixed(1)})
              </span>
            </div>
            <div className="telem-row">
              <span>Altitude:</span>
              <span>{selectedUAVData.position.y.toFixed(1)} m</span>
            </div>
            <div className="telem-row">
              <span>Speed:</span>
              <span>
                {Math.sqrt(
                  selectedUAVData.velocity.x**2 +
                  selectedUAVData.velocity.y**2 +
                  selectedUAVData.velocity.z**2
                ).toFixed(1)} m/s
              </span>
            </div>
            <div className="telem-row">
              <span>Velocity:</span>
              <span>
                ({selectedUAVData.velocity.x.toFixed(1)},
                {selectedUAVData.velocity.y.toFixed(1)},
                {selectedUAVData.velocity.z.toFixed(1)})
              </span>
            </div>
            <div className="telem-row">
              <span>Heading:</span>
              <span>
                {(Math.atan2(selectedUAVData.heading.z, selectedUAVData.heading.x) * 180 / Math.PI + 360).toFixed(0) % 360}°
              </span>
            </div>
          </>
        ) : (
          <p className="empty-msg">No drone selected.</p>
        )}
        {noSelection && selectedUAV && selectedUAVData && selectedSector != null && (
          <p className="empty-msg">Selected drone is not in the focused sector.</p>
        )}
      </div>

      {/* Mission Actions */}
      <h3>Actions{selectedSector != null ? ` (${activeSector ? activeSector.name : ''})` : ''}</h3>
      <div className="panel-section">
        <div className="action-grid">
          <button
            disabled={actionsDisabled}
            onClick={() => sendCommand({command: 'hover', drone_id: selectedUAV, sector_id: selectedSector})}
          >
            Hover
          </button>
          <button
            disabled={actionsDisabled}
            onClick={() => sendCommand({command: 'waypoint', drone_id: selectedUAV, sector_id: selectedSector})}
          >
            Waypoint
          </button>
          <button
            disabled={actionsDisabled}
            onClick={() => sendCommand({command: 'patrol', drone_id: selectedUAV, sector_id: selectedSector})}
          >
            Patrol
          </button>
          <button
            disabled={actionsDisabled}
            onClick={() => sendCommand({command: 'return_home', drone_id: selectedUAV, sector_id: selectedSector})}
          >
            Return Home
          </button>
        </div>
        <button
          className="full-btn remove-uav-btn"
          disabled={!connected || !selectedUAV || !selectedUAVData}
          onClick={() => sendCommand({command: 'remove', drone_id: selectedUAV})}
        >
          🗑 Remove Selected UAV
        </button>
      </div>

      {/* Path Planning */}
      <h3>Path Planning</h3>
      <div className="panel-section">
        <div className="planning-controls">
          <button
            className={`full-btn ${isSelectingDestination ? 'btn-active' : ''}`}
            onClick={() => setIsSelectingDestination(!isSelectingDestination)}
            disabled={actionsDisabled}
          >
            {isSelectingDestination ? 'Cancel Selection' : 'Select Destination'}
          </button>

          <div className="plan-row" style={{ flexDirection: 'column', alignItems: 'flex-start', margin: '6px 0' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>Destination:</span>
            {displayDest ? (
              <div style={{ fontSize: '0.85rem', fontFamily: 'monospace', paddingLeft: '8px' }}>
                X: {displayDest.x.toFixed(2)} m<br/>
                Y: {displayDest.y.toFixed(2)} m<br/>
                Z: {displayDest.z.toFixed(2)} m
              </div>
            ) : (
              <div style={{ fontSize: '0.85rem', paddingLeft: '8px', color: 'var(--text-dim)' }}>
                None selected
              </div>
            )}
          </div>

          <div className="plan-row">
            <label>Planner:</label>
            <select
              value={planner}
              onChange={(e) => setPlanner(e.target.value)}
              disabled={actionsDisabled}
            >
              <option value="A*">A*</option>
              <option value="RRT">RRT</option>
              <option value="RRT*">RRT*</option>
              <option value="Straight">Straight Line</option>
            </select>
          </div>
          <button
            className="full-btn plan-btn"
            onClick={() => {
              if (selectedDestination) {
                sendCommand({
                  command: 'plan_path',
                  drone_id: selectedUAV,
                  planner: planner,
                  dest: selectedDestination,
                  sector_id: selectedSector
                });
                setIsSelectingDestination(false);
              }
            }}
            disabled={actionsDisabled || !selectedDestination}
          >
            Plan Path
          </button>
          <button
            className="full-btn"
            onClick={() => {
              setSelectedDestination(null);
              setIsSelectingDestination(false);
            }}
            disabled={!selectedDestination}
          >
            Clear Destination
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusArea({ status, simTime, uavCount, paused }) {
  return (
    <div className="panel status-area">
      <div className="status-item">
        <span className={`status-dot ${status === 'Connected' ? 'dot-connected' : 'dot-disconnected'}`}></span>
        {status}
      </div>
      <div className="status-item">Sim Time: {simTime ? simTime.toFixed(2) : "0.00"}s</div>
      <div className="status-item">UAVs: {uavCount}</div>
      <div className="status-item">{paused ? "⏸ PAUSED" : "▶ RUNNING"}</div>
    </div>
  );
}

function App() {
  const { environment, simState, status, sendCommand, zoneEvents } = useSimulationSocket("ws://localhost:8765");
  const connected = status === 'Connected';
  const [selectedUAV, setSelectedUAV] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [isSelectingDestination, setIsSelectingDestination] = useState(false);
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [hoveredDestination, setHoveredDestination] = useState(null);
  const [currentAltitude, setCurrentAltitude] = useState(8);

  const sectors = simState.zones ? simState.zones.sectors : [];

  // Find the selected UAV data from the current state
  const selectedUAVData = simState.uavs
    ? simState.uavs.find(u => u.id === selectedUAV)
    : null;

  // Auto-select first UAV (within the focused sector if one is active)
  useEffect(() => {
    if (!simState.uavs || simState.uavs.length === 0) return;
    const candidates = selectedSector == null
      ? simState.uavs
      : simState.uavs.filter(u => u.sector === selectedSector);
    const stillValid = candidates.some(u => u.id === selectedUAV);
    if (!stillValid && candidates.length > 0) {
      setSelectedUAV(candidates[0].id);
    }
  }, [simState.uavs, selectedUAV, selectedSector]);

  // Clear destination when switching UAVs or sectors
  useEffect(() => {
    setSelectedDestination(null);
    setIsSelectingDestination(false);
  }, [selectedUAV, selectedSector]);

  // Handle altitude initialization
  useEffect(() => {
    if (isSelectingDestination && selectedUAVData && !selectedDestination) {
      setCurrentAltitude(selectedUAVData.position.y);
    } else if (!isSelectingDestination) {
      setHoveredDestination(null);
    }
  }, [isSelectingDestination, selectedUAVData, selectedDestination]);

  return (
    <div className="app-container">
      <TopBar paused={simState.paused} sendCommand={sendCommand} connected={connected} />
      <div className="main-content">
        <LeftPanel
          environment={environment}
          connected={connected}
          uavs={simState.uavs}
          selectedUAV={selectedUAV}
          onSelectUAV={setSelectedUAV}
          sendCommand={sendCommand}
          sectors={sectors}
          selectedSector={selectedSector}
          onSelectSector={setSelectedSector}
          zoneEvents={zoneEvents}
        />
        <div className="viewport">
          <SimulationScene
            environment={environment}
            simState={simState}
            selectedUAV={selectedUAV}
            selectedUAVData={selectedUAVData}
            onSelectUAV={setSelectedUAV}
            isSelectingDestination={isSelectingDestination}
            setSelectedDestination={setSelectedDestination}
            selectedDestination={selectedDestination}
            hoveredDestination={hoveredDestination}
            setHoveredDestination={setHoveredDestination}
            currentAltitude={currentAltitude}
            setCurrentAltitude={setCurrentAltitude}
            sectors={sectors}
            selectedSector={selectedSector}
            onSelectSector={setSelectedSector}
          />
        </div>
        <RightPanel
          selectedUAVData={selectedUAVData}
          selectedUAV={selectedUAV}
          connected={connected}
          sendCommand={sendCommand}
          isSelectingDestination={isSelectingDestination}
          setIsSelectingDestination={setIsSelectingDestination}
          selectedDestination={selectedDestination}
          setSelectedDestination={setSelectedDestination}
          hoveredDestination={hoveredDestination}
          sectors={sectors}
          selectedSector={selectedSector}
        />
      </div>
      <StatusArea
        status={status}
        simTime={simState.time}
        uavCount={simState.uavs ? simState.uavs.length : 0}
        paused={simState.paused}
      />
    </div>
  );
}

export default App;
