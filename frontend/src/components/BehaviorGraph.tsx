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

const NODE_COLORS: Record<string, string> = {
  function: '#3b82f6',
  state: '#8b5cf6',
  condition: '#eab308',
  hardware_output: '#10b981',
  hardware_input: '#f97316'
};

export default function BehaviorGraph({ runId }: { runId: string | null }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/runs/${runId}/behavior`)
      .then(res => res.json())
      .then(data => {
        if (data.nodes && data.edges) {
          const formattedNodes = data.nodes.map((n: any) => ({
            id: n.id,
            position: n.position || { x: Math.random() * 500, y: Math.random() * 500 }, // Fallback layout
            data: { label: n.label },
            style: {
              background: '#1a1a1a',
              color: '#fff',
              border: `2px solid ${NODE_COLORS[n.kind] || '#666'}`,
              borderRadius: '8px',
              padding: '10px',
              fontFamily: 'JetBrains Mono',
              fontSize: '12px'
            }
          }));

          const formattedEdges = data.edges.map((e: any, i: number) => ({
            id: `e-${i}`,
            source: e.source,
            target: e.target,
            animated: true,
            label: e.label,
            style: { stroke: '#666', strokeWidth: 2 },
            labelStyle: { fill: '#aaa', fontWeight: 700, fontSize: 10 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#666' }
          }));

          setNodes(formattedNodes);
          setEdges(formattedEdges);
        }
      })
      .catch(console.error);
  }, [runId, setNodes, setEdges]);

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 pb-2">
        <h2 className="text-2xl font-bold">Behavior Graph</h2>
        <p className="text-gray-400 text-sm mt-1">Firmware state machine and functional mapping</p>
      </div>
      <div className="flex-1 w-full bg-agent-900 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          colorMode="dark"
        >
          <Controls className="bg-agent-800 fill-white" />
          <MiniMap nodeStrokeColor={(n) => n.style?.borderColor as string} nodeColor="#1a1a1a" maskColor="rgba(0,0,0,0.7)" />
          <Background color="#333" gap={16} />
        </ReactFlow>
      </div>
    </div>
  );
}
