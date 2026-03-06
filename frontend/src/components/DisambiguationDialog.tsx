import { useState } from "react";
import type { DisambiguationData } from "../hooks/useStreamSearch";

interface DisambiguationDialogProps {
  data: DisambiguationData;
  onConfirm: (clarification: string) => void;
}

export default function DisambiguationDialog({ data, onConfirm }: DisambiguationDialogProps) {
  const [clarification, setClarification] = useState("");

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/50 p-4">
      <div
        className="flex max-h-[calc(100vh-32px)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border p-5 shadow-xl"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="mb-4 flex-shrink-0">
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Clarify Entity
          </div>
          <p className="mt-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>
            {data.message}
          </p>
          {data.entityName && (
            <div
              className="mt-2 inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium"
              style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
            >
              {data.entityName}
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <textarea
            className="min-h-[110px] w-full rounded-xl border px-3 py-2 text-sm outline-none"
            style={{
              background: "var(--surface-2)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
            value={clarification}
            onChange={(e) => setClarification(e.target.value)}
            placeholder="Example: I mean OpenClaw the AI agent, not a robotics gripper."
          />
        </div>

        <div className="mt-4 flex flex-shrink-0 justify-end">
          <button
            className="rounded-xl px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-50"
            style={{ background: "var(--accent)", color: "var(--bg)" }}
            disabled={!clarification.trim()}
            onClick={() => onConfirm(clarification.trim())}
          >
            Continue Research
          </button>
        </div>
      </div>
    </div>
  );
}
