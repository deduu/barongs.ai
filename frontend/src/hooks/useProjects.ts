import { useCallback, useState } from "react";
import type { Project } from "../types";
import { getItem, setItem } from "../lib/storage";

const MAX_PROJECTS = 20;

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>(() =>
    getItem<Project[]>("projects", []),
  );
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  const persist = useCallback((ps: Project[]) => {
    setItem("projects", ps.slice(0, MAX_PROJECTS));
  }, []);

  const createProject = useCallback(
    (name: string): string => {
      const id = `proj-${Date.now()}`;
      const project: Project = { id, name: name.trim(), createdAt: Date.now() };
      setProjects((prev) => {
        const next = [project, ...prev];
        persist(next);
        return next;
      });
      setActiveProjectId(id);
      return id;
    },
    [persist],
  );

  const renameProject = useCallback(
    (id: string, name: string) => {
      setProjects((prev) => {
        const next = prev.map((p) =>
          p.id === id ? { ...p, name: name.trim() } : p,
        );
        persist(next);
        return next;
      });
    },
    [persist],
  );

  const deleteProject = useCallback(
    (id: string) => {
      setProjects((prev) => {
        const next = prev.filter((p) => p.id !== id);
        persist(next);
        return next;
      });
      setActiveProjectId((prev) => (prev === id ? null : prev));
    },
    [persist],
  );

  return {
    projects,
    activeProjectId,
    setActiveProjectId,
    createProject,
    renameProject,
    deleteProject,
  } as const;
}
