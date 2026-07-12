"use client";

import { useEffect, useMemo, useState } from "react";
import { Background, Controls, Edge, Node, ReactFlow, useEdgesState, useNodesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ApiError,
  ArchitectureGraphResponse,
  TourStep,
  getArchitectureGraph,
  getTour,
} from "@/lib/api";
import { useHighlightedGraph } from "@/lib/graphHighlight";
import { Legend, TIER_LABELS, TIER_STYLES, layoutGraph } from "@/components/ModuleArchitectureGraph";

interface ExploreTourViewProps {
  repoName: string | null;
  disabled: boolean;
  onExitTour: () => void;
  onAskInChat: (question: string) => void;
}

const SLOW_LOAD_THRESHOLD_MS = 1200;

export default function ExploreTourView({ repoName, disabled, onExitTour, onAskInChat }: ExploreTourViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isSlowLoad, setIsSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<ArchitectureGraphResponse | null>(null);
  const [steps, setSteps] = useState<TourStep[]>([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!repoName || disabled) {
      setGraphData(null);
      setSteps([]);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setIsSlowLoad(false);
    setError(null);
    setStepIndex(0);

    const slowLoadTimer = setTimeout(() => {
      if (!cancelled) setIsSlowLoad(true);
    }, SLOW_LOAD_THRESHOLD_MS);

    Promise.all([getArchitectureGraph(repoName), getTour(repoName)])
      .then(([graph, tour]) => {
        if (cancelled) return;
        setGraphData(graph);
        setSteps(tour.steps);
      })
      .catch((err) => {
        if (cancelled) return;
        setGraphData(null);
        setSteps([]);
        setError(err instanceof ApiError ? err.message : "Failed to reach the server.");
      })
      .finally(() => {
        if (cancelled) return;
        clearTimeout(slowLoadTimer);
        setIsLoading(false);
        setIsSlowLoad(false);
      });

    return () => {
      cancelled = true;
      clearTimeout(slowLoadTimer);
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

  const currentStep = steps[stepIndex] ?? null;

  const { displayNodes, displayEdges } = useHighlightedGraph(
    nodes,
    edges,
    graphData?.edges ?? [],
    currentStep?.module_id ?? null
  );

  function goPrev() {
    setStepIndex((index) => Math.max(0, index - 1));
  }

  function goNext() {
    if (stepIndex >= steps.length - 1) {
      onExitTour();
      return;
    }
    setStepIndex((index) => Math.min(steps.length - 1, index + 1));
  }

  if (!repoName) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-text-muted">Select a repo to start its guided tour.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-text-muted">
          {isSlowLoad
            ? "Generating your guided tour for the first time — this takes a moment..."
            : "Loading tour..."}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-danger">{error}</p>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0 || steps.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-text-muted">No guided tour available for this repo.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-border px-8 py-5">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-text-primary">Explore Tour</h1>
          <span className="rounded-full border border-border-strong px-2.5 py-0.5 font-mono text-xs text-text-secondary">
            {repoName}
          </span>
        </div>
        <button
          type="button"
          onClick={onExitTour}
          className="font-mono text-xs text-text-secondary hover:text-text-primary"
        >
          Exit tour
        </button>
      </header>

      <div className="relative flex-1">
        <ReactFlow
          nodes={displayNodes}
          edges={displayEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
        </ReactFlow>

        <div className="absolute left-4 top-4">
          <Legend />
        </div>

        {currentStep && (
          <aside className="absolute right-4 top-4 bottom-4 z-10 w-96 overflow-y-auto rounded-lg border border-border-strong bg-bg-inset p-5 shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-mono text-xs font-bold uppercase tracking-wide text-accent">
                Onboarding tour
              </span>
              <span className="font-mono text-xs text-text-muted">
                Step {stepIndex + 1} of {steps.length}
              </span>
            </div>

            <span
              className="mb-3 inline-flex w-fit items-center rounded-full px-2.5 py-0.5 font-mono text-xs"
              style={{
                background: TIER_STYLES[currentStep.tier].background,
                color: TIER_STYLES[currentStep.tier].color,
                border: TIER_STYLES[currentStep.tier].border as string,
              }}
            >
              {TIER_LABELS[currentStep.tier]}
            </span>

            <h2 className="mb-3 font-bold text-text-primary">{currentStep.title}</h2>
            <p className="mb-5 whitespace-pre-wrap text-sm leading-6 text-text-secondary">
              {currentStep.narration}
            </p>

            {currentStep.key_functions.length > 0 && (
              <div className="mb-5">
                <h3 className="mb-2 font-mono text-xs font-bold uppercase tracking-wide text-text-muted">
                  Key functions
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {currentStep.key_functions.map((fn) => (
                    <span
                      key={fn}
                      className="truncate rounded-full border border-border-strong bg-surface px-2 py-0.5 font-mono text-xs text-text-secondary"
                    >
                      {fn}
                    </span>
                  ))}
                </div>
                {currentStep.function_count > currentStep.key_functions.length && (
                  <p className="mt-1 font-mono text-xs text-text-muted">
                    +{currentStep.function_count - currentStep.key_functions.length} more
                  </p>
                )}
              </div>
            )}

            <button
              type="button"
              onClick={() =>
                onAskInChat(`Explain what ${currentStep.label} does and how it fits into this codebase.`)
              }
              className="mb-5 w-full rounded-md border border-border-strong px-3 py-2 font-mono text-xs font-bold text-text-secondary hover:bg-surface-hover"
            >
              Ask about this module
            </button>

            <div className="flex items-center justify-between gap-2">
              <div className="flex gap-1.5">
                {steps.map((step, index) => (
                  <span
                    key={step.module_id}
                    className={`h-1.5 w-1.5 rounded-full ${
                      index === stepIndex ? "bg-accent" : "bg-border-strong"
                    }`}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={goPrev}
                  disabled={stepIndex === 0}
                  className="rounded-md border border-border-strong px-3 py-1.5 font-mono text-xs font-bold text-text-secondary disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  type="button"
                  onClick={goNext}
                  className="rounded-md bg-accent px-3 py-1.5 font-mono text-xs font-bold text-accent-foreground hover:bg-accent-strong"
                >
                  {stepIndex >= steps.length - 1 ? "Finish" : "Next"}
                </button>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
