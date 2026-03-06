import { useState } from "react";
import type { OutlineData } from "../hooks/useStreamSearch";
import type { OutlineSection, ResearchTask } from "../lib/api";

interface OutlineEditorProps {
  outline: OutlineData;
  onConfirm: (sections?: OutlineSection[], tasks?: ResearchTask[]) => void;
}

export default function OutlineEditor({ outline, onConfirm }: OutlineEditorProps) {
  const [sections, setSections] = useState<OutlineSection[]>(outline.sections);
  const [tasks, setTasks] = useState<ResearchTask[]>(outline.researchTasks);

  const updateSection = (idx: number, field: keyof OutlineSection, value: string) => {
    setSections((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)));
  };

  const removeSection = (idx: number) => {
    setSections((prev) => prev.filter((_, i) => i !== idx));
  };

  const addSection = () => {
    setSections((prev) => [...prev, { heading: "New Section", description: "" }]);
  };

  const updateTask = (idx: number, field: keyof ResearchTask, value: string) => {
    setTasks((prev) => prev.map((t, i) => (i === idx ? { ...t, [field]: value } : t)));
  };

  const removeTask = (idx: number) => {
    setTasks((prev) => prev.filter((_, i) => i !== idx));
  };

  const addTask = () => {
    setTasks((prev) => [
      ...prev,
      {
        task_id: `t${prev.length + 1}`,
        query: "",
        task_type: "secondary_web",
        agent_name: "deep_web_researcher",
        depends_on: [],
      },
    ]);
  };

  const inputStyle = {
    background: "var(--surface-2)",
    borderColor: "var(--border)",
    color: "var(--text)",
  } as const;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-4 flex-shrink-0">
        <h3 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
          Research Outline
        </h3>
        <p className="mt-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>
          Review the plan before deep research starts.
        </p>
        <p className="mt-2 text-[12px]" style={{ color: "var(--text-muted)" }}>
          Query: {outline.query}
        </p>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
        <div
          className="flex min-h-0 flex-col rounded-xl border p-4"
          style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
        >
          <div className="mb-3 flex flex-shrink-0 items-center justify-between">
            <h4 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Report Sections
            </h4>
            <button
              className="rounded-lg px-2 py-1 text-xs"
              style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}
              onClick={addSection}
            >
              Add Section
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            {sections.map((section, idx) => (
              <div key={`${section.heading}-${idx}`} className="rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
                <input
                  className="mb-2 w-full rounded-lg border px-3 py-2 text-sm outline-none"
                  style={inputStyle}
                  value={section.heading}
                  onChange={(e) => updateSection(idx, "heading", e.target.value)}
                  placeholder="Section heading"
                />
                <input
                  className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                  style={inputStyle}
                  value={section.description}
                  onChange={(e) => updateSection(idx, "description", e.target.value)}
                  placeholder="Description"
                />
                <div className="mt-2 flex justify-end">
                  <button
                    className="text-xs"
                    style={{ color: "#ef4444" }}
                    onClick={() => removeSection(idx)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div
          className="flex min-h-0 flex-col rounded-xl border p-4"
          style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
        >
          <div className="mb-3 flex flex-shrink-0 items-center justify-between">
            <h4 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Research Tasks
            </h4>
            <button
              className="rounded-lg px-2 py-1 text-xs"
              style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}
              onClick={addTask}
            >
              Add Task
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            {tasks.map((task, idx) => (
              <div key={`${task.task_id}-${idx}`} className="rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
                <input
                  className="mb-2 w-full rounded-lg border px-3 py-2 text-sm outline-none"
                  style={inputStyle}
                  value={task.query}
                  onChange={(e) => updateTask(idx, "query", e.target.value)}
                  placeholder="Search query"
                />
                <div className="grid gap-2 sm:grid-cols-2">
                  <select
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={inputStyle}
                    value={task.task_type}
                    onChange={(e) => updateTask(idx, "task_type", e.target.value)}
                  >
                    <option value="secondary_web">Web Search</option>
                    <option value="secondary_academic">Academic Search</option>
                    <option value="primary_code">Code Analysis</option>
                    <option value="fact_check">Fact Check</option>
                  </select>
                  <select
                    className="w-full rounded-lg border px-3 py-2 text-sm outline-none"
                    style={inputStyle}
                    value={task.agent_name}
                    onChange={(e) => updateTask(idx, "agent_name", e.target.value)}
                  >
                    <option value="deep_web_researcher">Web Researcher</option>
                    <option value="academic_researcher">Academic Researcher</option>
                    <option value="data_analyst">Data Analyst</option>
                    <option value="fact_checker">Fact Checker</option>
                  </select>
                </div>
                <div className="mt-2 flex justify-end">
                  <button
                    className="text-xs"
                    style={{ color: "#ef4444" }}
                    onClick={() => removeTask(idx)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-shrink-0 justify-end gap-2">
        <button
          className="rounded-xl border px-4 py-2 text-sm font-medium"
          style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
          onClick={() => onConfirm()}
        >
          Approve As-Is
        </button>
        <button
          className="rounded-xl px-4 py-2 text-sm font-medium"
          style={{ background: "var(--accent)", color: "var(--bg)" }}
          onClick={() => onConfirm(sections, tasks)}
        >
          Confirm With Edits
        </button>
      </div>
    </div>
  );
}
