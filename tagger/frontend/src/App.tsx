import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import NotFound from "./pages/NotFound";
import ProjectSetup from "./pages/ProjectSetup";
import TaggerDashboard from "./pages/TaggerDashboard";
import TaggerWorkspace from "./pages/TaggerWorkspace";
import ValidationReview from "./pages/ValidationReview";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<TaggerDashboard />} />
        <Route path="/projects/:id" element={<Navigate to="setup" replace />} />
        <Route path="/projects/:id/setup" element={<ProjectSetup />} />
        <Route path="/projects/:id/tag" element={<TaggerWorkspace />} />
        <Route path="/projects/:id/validate" element={<ValidationReview />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
