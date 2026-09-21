import { useEffect, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { motion } from 'framer-motion';
import { Code2, Cpu, Activity, Zap, Variable, Database } from 'lucide-react';

const CustomNode = ({ data }: any) => {
  const Icon = data.icon;
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05, zIndex: 50 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="relative px-5 py-4 bg-gradient-to-b from-[#0a0a0a]/90 to-[#050505]/95 backdrop-blur-xl rounded-2xl border min-w-[200px] overflow-hidden group cursor-pointer"
      style={{ 
        boxShadow: `0 0 30px ${data.shadowColor}, inset 0 1px 0 rgba(255,255,255,0.1)`, 
        borderColor: `${data.color}50` 
      }}
    >
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-20 transition-opacity duration-500 blur-xl pointer-events-none"
        style={{ backgroundColor: data.color }}
      ></div>

      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-white border-none shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
      
      <div className="flex items-center gap-4 relative z-10">
        <div 
          className="flex items-center justify-center w-10 h-10 rounded-xl border shadow-inner"
          style={{ backgroundColor: `${data.color}20`, borderColor: `${data.color}40`, color: data.color }}
        >
          <Icon size={20} className="drop-shadow-md" />
        </div>
        <div>
          <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase opacity-80">{data.kind}</div>
          <div className="text-sm font-mono font-bold text-white tracking-tight mt-0.5 group-hover:text-cyan-100 transition-colors">{data.label}</div>
        </div>
      </div>
      
      {data.file && (
        <div className="mt-3 pt-3 border-t border-white/5 relative z-10">
          <div className="text-[10px] text-gray-500 font-mono leading-relaxed truncate max-w-[180px]">
            {data.file}:{data.line}
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-white border-none shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
    </motion.div>
  );
};

const NODE_THEMES: Record<string, any> = {
  function: { color: '#3b82f6', shadowColor: 'rgba(59,130,246,0.15)', icon: Code2 },
  state: { color: '#8b5cf6', shadowColor: 'rgba(139,92,246,0.15)', icon: Database },
  condition: { color: '#eab308', shadowColor: 'rgba(234,179,8,0.15)', icon: Activity },
  hardware_output: { color: '#ef4444', shadowColor: 'rgba(239,68,68,0.15)', icon: Zap },
  hardware_input: { color: '#10b981', shadowColor: 'rgba(16,185,129,0.15)', icon: Cpu },
  constant: { color: '#6b7280', shadowColor: 'rgba(107,114,128,0.15)', icon: Variable }
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, edgesep: 50, ranksep: 120 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? 'left' : 'top';
    node.sourcePosition = isHorizontal ? 'right' : 'bottom';
    node.position = {
      x: nodeWithPosition.x - 110,
      y: nodeWithPosition.y - 40,
    };
    return node;
  });

  return { nodes, edges };
};

export default function BehaviorGraph({ runId }: { runId: string | null }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  
  const nodeTypes = useMemo(() => ({ custom: CustomNode }), []);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    
    const fetchGraph = () => {
      fetch(`/api/runs/${runId}/behavior`)
        .then(res => res.json())
        .then(data => {
          if (cancelled) return;
          if (data.nodes && data.edges) {
            const rawNodes = data.nodes.map((n: any) => {
              const theme = NODE_THEMES[n.kind] || NODE_THEMES.constant;
              return {
                id: n.id,
                type: 'custom',
                data: { 
                  label: n.label.length > 25 ? n.label.substring(0,25)+'...' : n.label,
                  kind: n.kind,
                  file: n.file,
                  line: n.line,
                  ...theme
                },
              };
            });

            const rawEdges = data.edges.map((e: any, i: number) => ({
              id: `e-${i}`,
              source: e.source,
              target: e.target,
              animated: true,
              label: e.kind,
              type: 'smoothstep',
              style: { 
                stroke: e.kind === 'controls' ? '#ef4444' : (e.kind === 'calls' ? '#3b82f6' : '#10b981'), 
                strokeWidth: 2,
                opacity: 0.8,
                filter: e.kind === 'controls' ? 'drop-shadow(0 0 8px rgba(239,68,68,0.8))' : 'drop-shadow(0 0 5px rgba(59,130,246,0.5))'
              },
              labelStyle: { fill: '#ffffff', fontWeight: 800, fontSize: 10, letterSpacing: '1px' },
              labelBgStyle: { fill: '#000000', fillOpacity: 0.8, rx: 6, ry: 6, stroke: '#333', strokeWidth: 1 },
              markerEnd: { 
                type: MarkerType.ArrowClosed, 
                color: e.kind === 'controls' ? '#ef4444' : (e.kind === 'calls' ? '#3b82f6' : '#10b981')
              }
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
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [runId, setNodes, setEdges]);

  return (
    <div className="h-full flex flex-col bg-[#050505] p-8 relative">
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-[100px] pointer-events-none -z-10"></div>
      
      <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} className="mb-6 z-10 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white">AST Semantic Graph</h2>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Control Flow & Hardware I/O Mapping</p>
        </div>
        <div className="flex gap-4 flex-wrap max-w-xl justify-end">
          {Object.entries(NODE_THEMES).map(([kind, theme]) => {
            const Icon = theme.icon;
            return (
              <div key={kind} className="flex items-center gap-2 text-[10px] font-mono text-gray-400 bg-white/5 px-2 py-1 rounded-md border border-white/5">
                <Icon size={12} color={theme.color} />
                {kind.toUpperCase()}
              </div>
            );
          })}
        </div>
      </motion.div>

      <div className="flex-1 w-full bg-[#030508]/80 backdrop-blur-sm rounded-2xl border border-white/5 overflow-hidden relative shadow-[0_0_50px_rgba(59,130,246,0.05)]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          minZoom={0.2}
          colorMode="dark"
          proOptions={{ hideAttribution: true }}
        >
          <Controls className="bg-[#0a0a0a] fill-white border-white/10 shadow-2xl" />
          <MiniMap 
            nodeColor={(n: any) => n.data?.color || '#0a0a0a'} 
            maskColor="rgba(3,5,8,0.8)" 
            className="bg-[#0a0a0a] border border-white/5 rounded-xl overflow-hidden" 
          />
          <Background color="#111" gap={20} size={1.5} />
        </ReactFlow>
      </div>
    </div>
  );
}
