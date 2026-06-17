import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Briefcase,
  Upload,
  Plus,
  Sparkles,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { useJobs } from "@/lib/store";

const mainItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Upload Candidate", url: "/upload", icon: Upload },
  { title: "New Job", url: "/jobs/new", icon: Plus },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const jobs = useJobs();

  const isActive = (path: string) =>
    path === "/" ? pathname === "/" : pathname.startsWith(path);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <Link
          to="/"
          className="flex items-center gap-2 px-2 py-2 group"
        >
          <div className="h-8 w-8 rounded-md bg-gradient-to-br from-primary to-gem flex items-center justify-center shadow-[0_0_20px_-4px_var(--color-primary)]">
            <Sparkles className="h-4 w-4 text-background" strokeWidth={2.5} />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-tight">
              <span className="font-display font-semibold text-sm tracking-tight">
                TalentDNA<span className="text-primary">.ai</span>
              </span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Recruiter OS
              </span>
            </div>
          )}
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)}>
                    <Link to={item.url} className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Active Requisitions</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {jobs.map((j) => (
                <SidebarMenuItem key={j.id}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith(`/jobs/${j.id}`)}
                  >
                    <Link
                      to="/jobs/$jobId"
                      params={{ jobId: j.id }}
                      className="flex items-center gap-2"
                    >
                      <Briefcase className="h-4 w-4 text-muted-foreground" />
                      {!collapsed && (
                        <span className="truncate text-sm">{j.title}</span>
                      )}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        {!collapsed && (
          <div className="px-2 py-2 text-[10px] uppercase tracking-[0.16em] text-muted-foreground font-mono">
            v0.9 · hackathon build
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
