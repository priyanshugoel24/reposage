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
  onAskInChat: (question: string) => void;
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

const TIER_LABELS: Record<ArchitectureTier, string> = {
  entry_point: "Entry point",
  core_service: "Core service",
  utility: "Utility",
};

function Legend() {
  const items: { tier: ArchitectureTier; label: string }[] = [
    { tier: "entry_point", label: TIER_LABELS.entry_point },
    { tier: "core_service", label: TIER_LABELS.core_service },
    { tier: "utility", label: TIER_LABELS.utility },
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

function ModuleDetailPanel({
  node,
  dependencyCount,
  dependentCount,
  onClose,
  onAskInChat,
}: {
  node: ArchitectureGraphResponse["nodes"][number];
  dependencyCount: number;
  dependentCount: number;
  onClose: () => void;
  onAskInChat: () => void;
}) {
  const extraFunctionCount = Math.max(0, node.function_count - node.functions.length);

  return (
    <aside className="absolute right-3 top-3 bottom-3 z-10 w-80 overflow-y-auto rounded-lg border border-border-strong bg-bg-inset p-5 shadow-2xl">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex flex-col gap-2">
          <h3 className="break-all font-mono text-sm font-bold text-text-primary">{node.label}</h3>
          <span
            className="inline-flex w-fit items-center rounded-full px-2.5 py-0.5 font-mono text-xs"
            style={{
              background: TIER_STYLES[node.tier].background,
              color: TIER_STYLES[node.tier].color,
              border: TIER_STYLES[node.tier].border as string,
            }}
          >
            {TIER_LABELS[node.tier]}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 text-text-muted hover:text-text-primary"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="mb-5 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-md border border-border bg-surface px-2 py-2">
          <div className="font-mono text-base font-bold text-text-primary">{node.function_count}</div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Functions</div>
        </div>
        <div className="rounded-md border border-border bg-surface px-2 py-2">
          <div className="font-mono text-base font-bold text-text-primary">{dependencyCount}</div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Deps</div>
        </div>
        <div className="rounded-md border border-border bg-surface px-2 py-2">
          <div className="font-mono text-base font-bold text-text-primary">{dependentCount}</div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-text-muted">Dependents</div>
        </div>
      </div>

      <div className="mb-5">
        <h4 className="mb-2 font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
          Key functions
        </h4>
        {node.functions.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {node.functions.map((fn) => (
              <li key={fn} className="truncate font-mono text-xs text-text-secondary">
                {fn}
              </li>
            ))}
          </ul>
        ) : (
          <p className="font-mono text-xs text-text-muted">No functions found.</p>
        )}
        {extraFunctionCount > 0 && (
          <p className="mt-1 font-mono text-xs text-text-muted">+{extraFunctionCount} more</p>
        )}
      </div>

      <button
        type="button"
        onClick={onAskInChat}
        className="w-full rounded-md bg-accent px-3 py-2 font-mono text-xs font-bold text-accent-foreground hover:bg-accent-strong"
      >
        Ask about this module
      </button>
    </aside>
  );
}

export default function ModuleArchitectureGraph({ repoName, disabled, onAskInChat }: ModuleArchitectureGraphProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<ArchitectureGraphResponse | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    if (!repoName || disabled) {
      setGraphData(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setSelectedNodeId(null);

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

  const selectedNode = useMemo(
    () => (selectedNodeId ? graphData?.nodes.find((n) => n.id === selectedNodeId) ?? null : null),
    [graphData, selectedNodeId]
  );

  const connectivity = useMemo(() => {
    if (!selectedNodeId || !graphData) return null;
    const connectedNodeIds = new Set<string>([selectedNodeId]);
    const connectedEdgeIds = new Set<string>();
    let dependencyCount = 0;
    let dependentCount = 0;
    for (const edge of graphData.edges) {
      if (edge.source === selectedNodeId) {
        connectedNodeIds.add(edge.target);
        connectedEdgeIds.add(`${edge.source}-${edge.target}`);
        dependencyCount += 1;
      }
      if (edge.target === selectedNodeId) {
        connectedNodeIds.add(edge.source);
        connectedEdgeIds.add(`${edge.source}-${edge.target}`);
        dependentCount += 1;
      }
    }
    return { connectedNodeIds, connectedEdgeIds, dependencyCount, dependentCount };
  }, [selectedNodeId, graphData]);

  const displayNodes = useMemo(() => {
    return nodes.map((node) => {
      const isSelected = connectivity !== null && node.id === selectedNodeId;
      const isConnected = connectivity === null || connectivity.connectedNodeIds.has(node.id);
      const baseBorder = (node.style as { border?: string } | undefined)?.border;

      return {
        ...node,
        style: {
          ...node.style,
          opacity: isConnected ? 1 : 0.25,
          boxShadow: isSelected
            ? "0 0 0 2px var(--color-accent), 0 0 14px var(--color-accent)"
            : "none",
          border: isSelected ? "1px solid var(--color-accent)" : baseBorder,
        },
      };
    });
  }, [nodes, connectivity, selectedNodeId]);

  const displayEdges = useMemo(() => {
    if (!connectivity) return edges;
    return edges.map((edge) => {
      const isConnected = connectivity.connectedEdgeIds.has(edge.id);
      return {
        ...edge,
        style: {
          ...edge.style,
          opacity: isConnected ? 1 : 0.15,
          stroke: isConnected ? "var(--color-accent)" : (edge.style as { stroke?: string } | undefined)?.stroke,
        },
        markerEnd: isConnected
          ? { type: MarkerType.ArrowClosed, color: "var(--color-accent)" }
          : edge.markerEnd,
      };
    });
  }, [edges, connectivity]);

  function handleNodeClick(nodeId: string) {
    setSelectedNodeId((current) => (current === nodeId ? null : nodeId));
  }

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
      <div className="relative h-[560px] rounded-md border border-border bg-bg-inset">
        <ReactFlow
          nodes={displayNodes}
          edges={displayEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, node) => handleNodeClick(node.id)}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
        </ReactFlow>

        {selectedNode && connectivity && (
          <ModuleDetailPanel
            node={selectedNode}
            dependencyCount={connectivity.dependencyCount}
            dependentCount={connectivity.dependentCount}
            onClose={() => setSelectedNodeId(null)}
            onAskInChat={() =>
              onAskInChat(`Explain what ${selectedNode.label} does and how it fits into this codebase.`)
            }
          />
        )}
      </div>
    </div>
  );
}
