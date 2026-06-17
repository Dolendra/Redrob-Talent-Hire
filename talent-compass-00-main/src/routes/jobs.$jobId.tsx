import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/jobs/$jobId")({
  component: () => <Outlet />,
});
