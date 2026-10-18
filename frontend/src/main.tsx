import "./styles/theme.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AuthProvider } from "./app/auth";
import { FeedbackProvider } from "./app/feedback";
import { CapabilityDetailPage } from "./features/catalog/CapabilityDetailPage";
import { CatalogListPage } from "./features/catalog/CatalogListPage";
import { LoginPage } from "./features/login/LoginPage";
import { ProjectDetailPage } from "./features/projects/ProjectDetailPage";
import { ProjectListPage } from "./features/projects/ProjectListPage";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: "/projects", element: <ProjectListPage /> },
      { path: "/projects/:projectId", element: <ProjectDetailPage /> },
      { path: "/catalog", element: <CatalogListPage /> },
      { path: "/catalog/:capabilityId/:version", element: <CapabilityDetailPage /> },
      { path: "*", element: <Navigate to="/projects" replace /> },
    ],
  },
]);

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <FeedbackProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </FeedbackProvider>
    </StrictMode>,
  );
}
