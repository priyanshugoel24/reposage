"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
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
import {
  ApiError,
  BlastRadiusResponse,
  GetBlastRadiusResponse,
  getBlastRadius,
} from "@/lib/api";
import { useHighlightedGraph } from "@/lib/graphHighlight";
import AmbiguousCandidatePicker from "@/components/AmbiguousCandidatePicker";

interface BlastRadiusViewProps {
  repoName: string | null;
  disabled: boolean;
}

const NODE_WIDTH = 200;
const NODE_HEIGHT = 56;

/** Mirrors ModuleArchitectureGraph's layoutGraph (same dagre setup, same ReactFlow
 * node/edge shape), but styles by hop distance from the target function instead of
 * by module tier: distance is an open-ended integer rather than a fixed tier union,
 * so it needs interpolated intensity instead of a TIER_STYLES lookup table, and
 * function-level nodes carry no centrality to size by. */
function distanceStyle(distance: number | null, maxDistance: number): React.CSSProperties {
  if (distance === null) {
    return {
      background: "var(--color-surface)",
      color: "var(--color-text-secondary)",
      border: "1px solid var(--color-border-strong)",
    };
  }

  if (distance === 0) {
    return {
      background: "var(--color-accent)",
      color: "var(--color-accent-foreground)",
      border: "2px solid var(--color-accent-strong)",
    };
  }

  const intensity = maxDistance > 0 ? 1 - (distance - 1) / maxDistance : 1;
  const opacity = Math.max(0.25, Math.min(0.85, intensity));

  return {
    background: `color-mix(in srgb, var(--color-accent) ${Math.round(opacity * 100)}%, var(--color-bg-inset))`,
    color: "var(--color-text-primary)",
    border: "1px solid var(--color-accent)",
  };
}

function layoutBlastRadiusGraph(
  graph: BlastRadiusResponse
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

  const maxDistance = Math.max(0, ...graph.nodes.map((n) => n.distance ?? 0));

  const nodes: Node[] = graph.nodes.map((node) => {
    const position = dagreGraph.node(node.id);

    return {
      id: node.id,
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
      data: { label: node.label },
      style: {
        ...distanceStyle(node.distance, maxDistance),
        width: NODE_WIDTH,
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
    style: { stroke: "var(--color-border-strong)" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--color-border-strong)" },
  }));

  return { nodes, edges };
}

function DistanceLegend({ maxDistance }: { maxDistance: number }) {
  const distances = Array.from({ length: maxDistance + 1 }, (_, i) => i);

  return (
    <div className="flex items-center gap-4 rounded-md border border-border bg-bg-inset px-3 py-2 font-mono text-xs text-text-secondary">
      {distances.map((distance) => (
        <div key={distance} className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-sm"
            style={{
              background: distanceStyle(distance, maxDistance).background,
              border: distanceStyle(distance, maxDistance).border as string,
            }}
          />
          {distance === 0 ? "Target function" : `${distance} hop${distance > 1 ? "s" : ""} away`}
        </div>
      ))}
    </div>
  );
}

export default function BlastRadiusView({ repoName, disabled }: BlastRadiusViewProps) {
  const [functionName, setFunctionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GetBlastRadiusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  async function runBlastRadius(name: string) {
    if (isLoading || disabled || !repoName || !name) return;

    setIsLoading(true);
    setError(null);
    setSelectedNodeId(null);

    try {
      const response = await getBlastRadius(repoName, name);
      setResult(response);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runBlastRadius(functionName);
  }

  const resolvedResult = result && !result.ambiguous ? result : null;

  const layout = useMemo(
    () => (resolvedResult ? layoutBlastRadiusGraph(resolvedResult) : null),
    [resolvedResult]
  );

  useEffect(() => {
    if (layout) {
      setNodes(layout.nodes);
      setEdges(layout.edges);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [layout, setNodes, setEdges]);

  const { displayNodes, displayEdges } = useHighlightedGraph(
    nodes,
    edges,
    resolvedResult?.edges ?? [],
    selectedNodeId
  );

  const maxDistance = resolvedResult
    ? Math.max(0, ...resolvedResult.nodes.map((n) => n.distance ?? 0))
    : 0;

  const hasNoCallers = resolvedResult !== null && resolvedResult.nodes.length <= 1;

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <input
          type="text"
          value={functionName}
          onChange={(e) => setFunctionName(e.target.value)}
          placeholder={disabled ? "Ingest a repo first" : "Function name"}
          required
          disabled={disabled || isLoading}
          className="flex-1 rounded-md border border-border-strong bg-surface px-3 py-2 font-mono text-sm text-text-primary placeholder:text-text-muted disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || isLoading}
          className="rounded-md bg-accent px-4 py-2 font-mono text-sm font-bold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Analyzing..." : "Show blast radius"}
        </button>
      </form>

      {isLoading && <p className="text-sm text-text-muted">Analyzing...</p>}

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && result.ambiguous && (
        <AmbiguousCandidatePicker
          candidates={result.candidates}
          isLoading={isLoading}
          onResolve={runBlastRadius}
        />
      )}

      {resolvedResult && hasNoCallers && (
        <p className="text-sm text-text-muted">
          No other code in this repository currently calls this function.
        </p>
      )}

      {resolvedResult && !hasNoCallers && (
        <div className="flex flex-col gap-3">
          <p className="font-mono text-xs text-text-muted">
            {resolvedResult.qualified_name} &middot; {resolvedResult.nodes.length} functions &middot;{" "}
            {resolvedResult.edges.length} call edges
          </p>
          <DistanceLegend maxDistance={maxDistance} />
          <div className="relative h-[560px] rounded-md border border-border bg-bg-inset">
            <ReactFlow
              nodes={displayNodes}
              edges={displayEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={(_, node) =>
                setSelectedNodeId((current) => (current === node.id ? null : node.id))
              }
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
        </div>
      )}
    </div>
  );
}
