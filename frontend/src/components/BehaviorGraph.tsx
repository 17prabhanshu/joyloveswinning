import { useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { motion } from 'framer-motion';

const NODE_COLORS: Record<string, string> = {
  function: '#3b82f6',
  state: '#8b5cf6',
  condition: '#eab308',
  hardware_output: '#ef4444',
  hardware_input: '#10b981',
  constant: '#6b7280'
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 70, edgesep: 30, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 150, height: 50 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? 'left' : 'top';
    node.sourcePosition = isHorizontal ? 'right' : 'bottom';
    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - 75,
      y: nodeWithPosition.y - 25,
    };
    return node;
  });

  return { nodes, edges };
};

export default function BehaviorGraph({ runId }: { runId: string | null }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/runs/${runId}/behavior`)
      .then(res => res.json())
      .then(data => {
        if (data.nodes && data.edges) {
          const rawNodes = data.nodes.map((n: any) => ({
            id: n.id,
            data: { label: n.label.length > 20 ? n.label.substring(0,20)+'...' : n.label },
            style: {
              background: '#0a0a0a',
              color: '#fff',
              border: `2px solid ${NODE_COLORS[n.kind] || '#666'}`,
              borderRadius: '8px',
              padding: '10px',
              fontFamily: 'JetBrains Mono',
              fontSize: '11px',
              boxShadow: `0 0 15px ${NODE_COLORS[n.kind] || '#666'}40`,
              width: 150
            }
          }));

          const rawEdges = data.edges.map((e: any, i: number) => ({
            id: `e-${i}`,
            source: e.source,
            target: e.target,
            animated: true,
            label: e.kind,
            style: { stroke: '#4b5563', strokeWidth: 2 },
            labelStyle: { fill: '#9ca3af', fontWeight: 700, fontSize: 10, backgroundColor: '#0a0a0a' },
            labelBgStyle: { fill: '#0a0a0a', color: '#0a0a0a', fillOpacity: 0.8 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#4b5563' }
          }));

          const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            rawNodes,
            rawEdges,
            'TB'
          );

          setNodes(layoutedNodes);
          setEdges(layoutedEdges);
        }
      })
      .catch(console.error);
  }, [runId, setNodes, setEdges]);

  return (
    <div className="h-full flex flex-col bg-[#050505] p-6 relative">
      <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} className="mb-4 z-10 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white">AST Semantic Graph</h2>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Control Flow & Hardware I/O Mapping</p>
        </div>
        <div className="flex gap-4">
          {Object.entries(NODE_COLORS).map(([kind, color]) => (
            <div key={kind} className="flex items-center gap-2 text-xs font-mono text-gray-400">
              <span className="w-3 h-3 rounded-full" style={{backgroundColor: color}}></span>
              {kind.toUpperCase()}
            </div>
          ))}
        </div>
      </motion.div>
      <div className="flex-1 w-full bg-[#0a0a0a] rounded-2xl border border-white/10 overflow-hidden relative shadow-[0_0_50px_rgba(59,130,246,0.1)]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          colorMode="dark"
        >
          <Controls className="bg-agent-800 fill-white border-white/10" />
          <MiniMap nodeStrokeColor={(n) => n.style?.borderColor as string} nodeColor="#0a0a0a" maskColor="rgba(0,0,0,0.7)" />
          <Background color="#222" gap={16} />
        </ReactFlow>
      </div>
    </div>
  );
}
