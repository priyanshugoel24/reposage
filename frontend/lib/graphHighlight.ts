import { useMemo } from "react";
import { Edge, MarkerType, Node } from "@xyflow/react";
import { ArchitectureEdge } from "@/lib/api";

export interface GraphConnectivity {
  connectedNodeIds: Set<string>;
  connectedEdgeIds: Set<string>;
  dependencyCount: number;
  dependentCount: number;
}

export function computeConnectivity(
  edges: ArchitectureEdge[],
  highlightedNodeId: string | null
): GraphConnectivity | null {
  if (!highlightedNodeId) return null;

  const connectedNodeIds = new Set<string>([highlightedNodeId]);
  const connectedEdgeIds = new Set<string>();
  let dependencyCount = 0;
  let dependentCount = 0;

  for (const edge of edges) {
    if (edge.source === highlightedNodeId) {
      connectedNodeIds.add(edge.target);
      connectedEdgeIds.add(`${edge.source}-${edge.target}`);
      dependencyCount += 1;
    }
    if (edge.target === highlightedNodeId) {
      connectedNodeIds.add(edge.source);
      connectedEdgeIds.add(`${edge.source}-${edge.target}`);
      dependentCount += 1;
    }
  }

  return { connectedNodeIds, connectedEdgeIds, dependencyCount, dependentCount };
}

/** Dims nodes/edges unconnected to `highlightedNodeId`, matching the selected-node
 * treatment in the Architecture view's module graph. Shared so the Explore Tour graph
 * highlights its current step's module the same way. */
export function useHighlightedGraph(
  nodes: Node[],
  edges: Edge[],
  graphEdges: ArchitectureEdge[],
  highlightedNodeId: string | null
) {
  const connectivity = useMemo(
    () => computeConnectivity(graphEdges, highlightedNodeId),
    [graphEdges, highlightedNodeId]
  );

  const displayNodes = useMemo(() => {
    return nodes.map((node) => {
      const isSelected = connectivity !== null && node.id === highlightedNodeId;
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
  }, [nodes, connectivity, highlightedNodeId]);

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

  return { displayNodes, displayEdges, connectivity };
}
