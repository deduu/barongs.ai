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
        task_id: `t${prev.length}`,
        query: "",
        task_type: "secondary_web",
        agent_name: "deep_web_researcher",
        depends_on: [],
      },
    ]);
  };

  return (
    <div className="outline-editor">
      <h3>Research Outline</h3>
      <p className="outline-query">Query: {outline.query}</p>

      <div className="outline-panels">
        {/* Report Sections */}
        <div className="outline-panel">
          <h4>Report Sections</h4>
          {sections.map((s, i) => (
            <div key={i} className="outline-item">
              <input
                value={s.heading}
                onChange={(e) => updateSection(i, "heading", e.target.value)}
                placeholder="Section heading"
              />
              <input
                value={s.description}
                onChange={(e) => updateSection(i, "description", e.target.value)}
                placeholder="Description"
              />
              <button onClick={() => removeSection(i)} className="outline-remove" title="Remove section">
                &times;
              </button>
            </div>
          ))}
          <button onClick={addSection} className="outline-add">
            + Add Section
          </button>
        </div>

        {/* Research Tasks */}
        <div className="outline-panel">
          <h4>Research Tasks</h4>
          {tasks.map((t, i) => (
            <div key={i} className="outline-item">
              <input
                value={t.query}
                onChange={(e) => updateTask(i, "query", e.target.value)}
                placeholder="Search query"
              />
              <select
                value={t.task_type}
                onChange={(e) => updateTask(i, "task_type", e.target.value)}
              >
                <option value="secondary_web">Web Search</option>
                <option value="secondary_academic">Academic Search</option>
                <option value="code_analysis">Code Analysis</option>
              </select>
              <button onClick={() => removeTask(i)} className="outline-remove" title="Remove task">
                &times;
              </button>
            </div>
          ))}
          <button onClick={addTask} className="outline-add">
            + Add Task
          </button>
        </div>
      </div>

      <div className="outline-actions">
        <button onClick={() => onConfirm()} className="outline-approve">
          Approve as-is
        </button>
        <button onClick={() => onConfirm(sections, tasks)} className="outline-submit">
          Confirm with edits
        </button>
      </div>
    </div>
  );
}
