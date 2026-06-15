
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Navigate } from "react-router-dom";
import NotFound from "./pages/NotFound";
import HypercubePopOut from "./components/taxonomy/explorer/HypercubePopOut";
import TreeLocationsPopOut from "./components/taxonomy/explorer/TreeLocationsPopOut";
import { HelpProvider } from "./components/help/HelpProvider";
import TaggerDashboard from "./pages/TaggerDashboard";
import ProjectSetup from "./pages/ProjectSetup";
import TaggerWorkspace from "./pages/TaggerWorkspace";
import TaxonomyLab from "./pages/TaxonomyLab";
import ValidationReview from "./pages/ValidationReview";



const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <HelpProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TaggerDashboard />} />
          <Route path="/projects/:id" element={<Navigate to="setup" replace />} />
          <Route path="/projects/:id/setup" element={<ProjectSetup />} />
          <Route path="/projects/:id/tag" element={<TaggerWorkspace />} />
          <Route path="/projects/:id/validate" element={<ValidationReview />} />
          <Route path="/taxonomy-lab" element={<TaxonomyLab />} />
          <Route path="/hypercube-popout" element={<HypercubePopOut />} />
          <Route path="/tree-locations-popout" element={<TreeLocationsPopOut />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </HelpProvider>
  </QueryClientProvider>
);

export default App;
