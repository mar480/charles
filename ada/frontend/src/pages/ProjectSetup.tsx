import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject } from "@/components/tagger/api";
import ProjectSetupWizard from "@/components/tagger/ProjectSetupWizard";
import type { TaggerProject } from "@/components/tagger/types";

const ProjectSetup = () => {
  const { id = "" } = useParams();
  const [project, setProject] = useState<TaggerProject | null>(null);
  const [status, setStatus] = useState("Loading project...");

  useEffect(() => {
    void getProject(id)
      .then((nextProject) => {
        setProject(nextProject);
        setStatus("");
      })
      .catch((error: Error) => setStatus(error.message));
  }, [id]);

  if (!project) {
    return <main className="tagger-page"><p>{status}</p></main>;
  }

  return <main className="tagger-page"><ProjectSetupWizard project={project} onProjectChange={setProject} /></main>;
};

export default ProjectSetup;

