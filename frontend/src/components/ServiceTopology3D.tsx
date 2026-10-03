import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { ShieldCheck, AlertTriangle, Activity, RefreshCw, Cpu, Database, Server, Zap, Globe } from 'lucide-react';

interface NodeData {
  id: string;
  name: string;
  type: 'gateway' | 'service' | 'database' | 'cache' | 'external';
  status: 'healthy' | 'warning' | 'critical';
  latency: number;
  rpm: number;
  position: [number, number, number];
  color: number;
}

interface ServiceTopology3DProps {
  healthScore?: number;
  totalErrors?: number;
  onNodeClick?: (nodeId: string) => void;
}

export const ServiceTopology3D: React.FC<ServiceTopology3DProps> = ({
  healthScore = 95,
  totalErrors = 0,
  onNodeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const [isRotating, setIsRotating] = useState(true);

  // Derive node health from telemetry metrics
  const isDbCritical = totalErrors > 10;
  const isPaymentDegraded = totalErrors > 5;

  const nodesData: NodeData[] = [
    {
      id: 'gateway',
      name: 'API Gateway (Envoy/Traefik)',
      type: 'gateway',
      status: 'healthy',
      latency: 18,
      rpm: 420,
      position: [0, 1.8, 0],
      color: 0x3b82f6, // Blue
    },
    {
      id: 'ingest',
      name: 'PulseWatch Ingest Service',
      type: 'service',
      status: 'healthy',
      latency: 24,
      rpm: 380,
      position: [-2.2, 0.2, 0.8],
      color: 0x10b981, // Emerald
    },
    {
      id: 'database',
      name: 'PostgreSQL Primary (Pool: 20)',
      type: 'database',
      status: isDbCritical ? 'critical' : 'healthy',
      latency: isDbCritical ? 240 : 35,
      rpm: 210,
      position: [-1.2, -1.8, 1.2],
      color: isDbCritical ? 0xef4444 : 0x10b981, // Red or Emerald
    },
    {
      id: 'cache',
      name: 'Redis Cache Cluster (redis-02)',
      type: 'cache',
      status: totalErrors > 8 ? 'warning' : 'healthy',
      latency: 4,
      rpm: 540,
      position: [1.6, -1.5, 0.5],
      color: totalErrors > 8 ? 0xf59e0b : 0x10b981, // Amber or Emerald
    },
    {
      id: 'payments',
      name: 'Stripe Payment Gateway',
      type: 'external',
      status: isPaymentDegraded ? 'warning' : 'healthy',
      latency: isPaymentDegraded ? 320 : 85,
      rpm: 45,
      position: [2.5, 0.6, -0.6],
      color: isPaymentDegraded ? 0xf59e0b : 0x8b5cf6, // Amber or Purple
    },
    {
      id: 'client',
      name: 'Edge CDN & Web Clients',
      type: 'gateway',
      status: 'healthy',
      latency: 42,
      rpm: 650,
      position: [0, 3.4, -0.8],
      color: 0x06b6d4, // Cyan
    },
  ];

  // Connections between nodes
  const links: Array<[string, string]> = [
    ['client', 'gateway'],
    ['gateway', 'ingest'],
    ['gateway', 'payments'],
    ['ingest', 'database'],
    ['ingest', 'cache'],
  ];

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 340;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x090d16, 0.08);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    container.replaceChildren(renderer.domElement);

    // Grid Floor
    const gridHelper = new THREE.GridHelper(10, 20, 0x1e293b, 0x0f172a);
    gridHelper.position.y = -2.6;
    scene.add(gridHelper);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x38bdf8, 2, 20);
    pointLight.position.set(2, 4, 3);
    scene.add(pointLight);

    const redLight = new THREE.PointLight(0xef4444, isDbCritical ? 3 : 0.5, 10);
    redLight.position.set(-1.2, -1.8, 1.2);
    scene.add(redLight);

    // Node Meshes
    const nodeGroup = new THREE.Group();
    scene.add(nodeGroup);

    const meshMap = new Map<string, THREE.Mesh>();
    const nodeGeometry = new THREE.IcosahedronGeometry(0.38, 2);

    nodesData.forEach((node) => {
      const material = new THREE.MeshStandardMaterial({
        color: node.color,
        roughness: 0.2,
        metalness: 0.8,
        emissive: node.color,
        emissiveIntensity: node.status === 'critical' ? 0.8 : 0.35,
      });

      const mesh = new THREE.Mesh(nodeGeometry, material);
      mesh.position.set(...node.position);
      mesh.userData = { id: node.id, nodeData: node };
      nodeGroup.add(mesh);
      meshMap.set(node.id, mesh);

      // Glowing outer ring for critical/warning nodes
      if (node.status !== 'healthy') {
        const ringGeo = new THREE.RingGeometry(0.5, 0.58, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: node.color,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.copy(mesh.position);
        ring.rotation.x = Math.PI / 2;
        nodeGroup.add(ring);
      }
    });

    // Links (lines) between nodes
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x334155,
      transparent: true,
      opacity: 0.6,
    });

    links.forEach(([fromId, toId]) => {
      const fromNode = nodesData.find((n) => n.id === fromId);
      const toNode = nodesData.find((n) => n.id === toId);
      if (fromNode && toNode) {
        const points = [
          new THREE.Vector3(...fromNode.position),
          new THREE.Vector3(...toNode.position),
        ];
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(lineGeo, lineMaterial);
        nodeGroup.add(line);
      }
    });

    // Animated particles along links
    const particleCount = 40;
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleProgress = new Float32Array(particleCount);
    const particleLinks = new Int32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      particleProgress[i] = Math.random();
      particleLinks[i] = Math.floor(Math.random() * links.length);
    }

    particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMaterial = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.08,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
    });
    const particleSystem = new THREE.Points(particleGeometry, particleMaterial);
    nodeGroup.add(particleSystem);

    // Mouse Interaction / Raycasting
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerDown = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(Array.from(meshMap.values()));
      if (intersects.length > 0) {
        const hit = intersects[0].object as THREE.Mesh;
        const data = hit.userData.nodeData as NodeData;
        setSelectedNode(data);
        if (onNodeClick) onNodeClick(data.id);
      }
    };

    container.addEventListener('click', handlePointerDown);

    // Animation Loop
    let animationFrameId: number;
    let lastTime = performance.now();
    const startTime = performance.now();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const currentTime = performance.now();
      const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
      lastTime = currentTime;
      const elapsed = (currentTime - startTime) / 1000;

      // Gentle auto-rotation
      if (isRotating) {
        nodeGroup.rotation.y += delta * 0.15;
      }

      // Pulse node scales
      meshMap.forEach((mesh, id) => {
        const node = nodesData.find((n) => n.id === id);
        if (node?.status === 'critical') {
          const s = 1 + Math.sin(elapsed * 6) * 0.12;
          mesh.scale.set(s, s, s);
        } else {
          mesh.rotation.y += delta * 0.5;
        }
      });

      // Update particle positions along connections
      const posArray = particleGeometry.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        particleProgress[i] = (particleProgress[i] + delta * 0.4) % 1.0;
        const linkIndex = particleLinks[i];
        const [fromId, toId] = links[linkIndex];
        const fromNode = nodesData.find((n) => n.id === fromId);
        const toNode = nodesData.find((n) => n.id === toId);

        if (fromNode && toNode) {
          const t = particleProgress[i];
          const x = THREE.MathUtils.lerp(fromNode.position[0], toNode.position[0], t);
          const y = THREE.MathUtils.lerp(fromNode.position[1], toNode.position[1], t);
          const z = THREE.MathUtils.lerp(fromNode.position[2], toNode.position[2], t);

          posArray[i * 3] = x;
          posArray[i * 3 + 1] = y;
          posArray[i * 3 + 2] = z;
        }
      }
      particleGeometry.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight || 340;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('click', handlePointerDown);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      particleGeometry.dispose();
      particleMaterial.dispose();
      nodeGeometry.dispose();
      lineMaterial.dispose();
    };
  }, [isRotating, isDbCritical, isPaymentDegraded, totalErrors]);

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'database':
        return <Database className="w-4 h-4 text-emerald-400" />;
      case 'cache':
        return <Zap className="w-4 h-4 text-amber-400" />;
      case 'gateway':
        return <Globe className="w-4 h-4 text-blue-400" />;
      case 'external':
        return <Cpu className="w-4 h-4 text-purple-400" />;
      default:
        return <Server className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <div className="relative w-full h-[360px] bg-slate-950/80 rounded-xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-md">
      {/* 3D WebGL Canvas */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Overlay Header */}
      <div className="absolute top-3 left-4 right-4 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700/60 px-3 py-1.5 rounded-lg backdrop-blur-sm pointer-events-auto">
          <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
            3D Service Mesh Topology
          </span>
          <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">
            LIVE GPU
          </span>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={() => setIsRotating(!isRotating)}
            className={`p-1.5 rounded-lg border text-xs font-mono transition-all flex items-center gap-1.5 ${
              isRotating
                ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle Auto Rotation"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRotating ? 'animate-spin' : ''}`} />
            <span className="text-[11px]">{isRotating ? 'Auto-Orbit ON' : 'Paused'}</span>
          </button>
        </div>
      </div>

      {/* Node Details HUD Card */}
      {selectedNode ? (
        <div className="absolute bottom-4 left-4 max-w-xs bg-slate-900/95 border border-slate-700/80 p-3.5 rounded-xl shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              {getNodeIcon(selectedNode.type)}
              <div>
                <h4 className="text-xs font-semibold text-slate-100">{selectedNode.name}</h4>
                <span className="text-[10px] font-mono text-slate-400 uppercase">
                  {selectedNode.type} node
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-500 hover:text-slate-300 text-xs p-1"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-3 pt-2.5 border-t border-slate-800 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-400 block">Avg Latency</span>
              <span className="text-slate-200 font-semibold">{selectedNode.latency}ms</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block">Throughput</span>
              <span className="text-slate-200 font-semibold">{selectedNode.rpm} req/m</span>
            </div>
            <div className="col-span-2 flex items-center justify-between pt-1">
              <span className="text-[10px] text-slate-400">Health Status:</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                  selectedNode.status === 'healthy'
                    ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                    : selectedNode.status === 'warning'
                    ? 'bg-amber-950/80 text-amber-400 border border-amber-800/60'
                    : 'bg-rose-950/80 text-rose-400 border border-rose-800/60 animate-pulse'
                }`}
              >
                {selectedNode.status}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="absolute bottom-3 left-4 bg-slate-900/80 border border-slate-800/60 px-3 py-1 rounded text-[11px] text-slate-400 font-mono pointer-events-none">
          Click any 3D node to inspect telemetry metrics & latency
        </div>
      )}

      {/* Legend Badge */}
      <div className="absolute bottom-3 right-4 flex items-center gap-3 bg-slate-900/80 border border-slate-800/60 px-3 py-1 rounded text-[11px] text-slate-400 font-mono pointer-events-none">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400" /> Healthy
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400" /> Warning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" /> Critical
        </span>
      </div>
    </div>
  );
};
