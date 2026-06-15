import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createProject, listProjects } from "@/components/tagger/api";
import type { TaggerProject } from "@/components/tagger/types";

const TaggerDashboard = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<TaggerProject[]>([]);
  const [status, setStatus] = useState("Loading projects...");

  useEffect(() => {
    void listProjects()
      .then((nextProjects) => {
        setProjects(nextProjects);
        setStatus(nextProjects.length ? `${nextProjects.length} project(s)` : "No projects yet.");
      })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  const handleCreate = async () => {
    const project = await createProject();
    navigate(`/projects/${project.id}/setup`);
  };

  return (
    <main className="tagger-page">
      <section className="tagger-hero">
        <div>
          <div className="tagger-eyebrow">Charles tagger</div>
          <h1>Companies House tagger dashboard</h1>
          <p className="tagger-muted">This branch now starts with project creation and filing setup. The public taxonomy viewer remains available as an internal expert tool at <code>/taxonomy-lab</code>.</p>
        </div>
        <div className="tagger-actions">
          <button type="button" className="tagger-button primary" onClick={() => void handleCreate()}>Create project</button>
        </div>
      </section>

      <section className="tagger-card">
        <h2>Recent projects</h2>
        <p className="tagger-muted">{status}</p>
        <div className="tagger-grid">
          {projects.map((project) => (
            <button key={project.id} className="tagger-card tagger-project-card" onClick={() => navigate(`/projects/${project.id}/setup`)}>
              <div className="tagger-eyebrow">{project.status}</div>
              <h3>{String(project.defaults["company.name"] || "Untitled project")}</h3>
              <p>{String(project.defaults["company.crn"] || "No CRN yet")}</p>
              <p>{project.id}</p>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
};

export default TaggerDashboard;

