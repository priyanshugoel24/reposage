"use client";

import { useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Edge,
  MarkerType,
  Node,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ApiError, ArchitectureGraphResponse, ArchitectureTier, getArchitectureGraph } from "@/lib/api";

interface ModuleArchitectureGraphProps {
  repoName: string | null;
  disabled: boolean;
}

const NODE_WIDTH = 180;
const NODE_HEIGHT = 56;
const MIN_SIZE = 140;
const MAX_SIZE = 260;

const TIER_STYLES: Record<ArchitectureTier, React.CSSProperties> = {
  entry_point: {
    background: "var(--color-accent)",
    color: "var(--color-accent-foreground)",
    border: "1px solid var(--color-accent-strong)",
  },
  core_service: {
    background: "var(--color-bg-inset)",
    color: "var(--color-text-primary)",
    border: "2px solid var(--color-accent)",
  },
  utility: {
    background: "var(--color-surface)",
    color: "var(--color-text-secondary)",
    border: "1px solid var(--color-border-strong)",
  },
};

function layoutGraph(
  graph: ArchitectureGraphResponse
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 100 });

  for (const node of graph.nodes) {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of graph.edges) {
    dagreGraph.setEdge(edge.source, edge.target);
  }

  dagre.layout(dagreGraph);

  const nodes: Node[] = graph.nodes.map((node) => {
    const position = dagreGraph.node(node.id);
    const size = MIN_SIZE + node.centrality * (MAX_SIZE - MIN_SIZE);

    return {
      id: node.id,
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
      data: { label: node.label },
      style: {
        ...TIER_STYLES[node.tier],
        width: size,
        fontSize: 12,
        fontFamily: "var(--font-mono)",
        borderRadius: 6,
        padding: 8,
        textAlign: "center",
      },
    };
  });

  const edges: Edge[] = graph.edges.map((edge) => ({
    id: `${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: String(edge.weight),
    style: { stroke: "var(--color-border-strong)" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--color-border-strong)" },
  }));

  return { nodes, edges };
}

function Legend() {
  const items: { tier: ArchitectureTier; label: string }[] = [
    { tier: "entry_point", label: "Entry point" },
    { tier: "core_service", label: "Core service" },
    { tier: "utility", label: "Utility" },
  ];

  return (
    <div className="flex items-center gap-4 rounded-md border border-border bg-bg-inset px-3 py-2 font-mono text-xs text-text-secondary">
      {items.map((item) => (
        <div key={item.tier} className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-sm"
            style={{
              background: TIER_STYLES[item.tier].background,
              border: TIER_STYLES[item.tier].border as string,
            }}
          />
          {item.label}
        </div>
      ))}
    </div>
  );
}

export default function ModuleArchitectureGraph({ repoName, disabled }: ModuleArchitectureGraphProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<ArchitectureGraphResponse | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!repoName || disabled) {
      setGraphData(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    getArchitectureGraph(repoName)
      .then((response) => {
        if (!cancelled) setGraphData(response);
      })
      .catch((err) => {
        if (cancelled) return;
        setGraphData(null);
        setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [repoName, disabled]);

  const layout = useMemo(() => (graphData ? layoutGraph(graphData) : null), [graphData]);

  useEffect(() => {
    if (layout) {
      setNodes(layout.nodes);
      setEdges(layout.edges);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [layout, setNodes, setEdges]);

  if (!repoName) {
    return <p className="text-sm text-text-muted">Select a repo to view its architecture graph.</p>;
  }

  if (isLoading) {
    return <p className="text-sm text-text-muted">Loading...</p>;
  }

  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!graphData || graphData.nodes.length === 0) {
    return <p className="text-sm text-text-muted">No architecture graph available for this repo.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <Legend />
      <div className="h-[560px] rounded-md border border-border bg-bg-inset">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, node) => console.log("Architecture node clicked:", node.id)}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
