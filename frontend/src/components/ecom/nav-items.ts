import {
  BarChart3,
  Bot,
  BookOpen,
  LayoutDashboard,
  LifeBuoy,
  MessageSquare,
  Settings,
  SquareKanban,
  Workflow,
  type LucideIcon,
} from "lucide-react";

/** Ecom-OS information architecture (Build Spec §7). Shared by the sidebar
 * and the ⌘K command palette so navigation stays in one place. */
export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
};

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/overview",
    label: "Overview",
    icon: LayoutDashboard,
    description: "Brand + per-store KPIs and today's tasks",
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    description: "Date ranges, comparison, funnel",
  },
  {
    href: "/tasks",
    label: "Tasks",
    icon: SquareKanban,
    description: "Per-person Kanban board",
  },
  {
    href: "/chat",
    label: "Chat",
    icon: MessageSquare,
    description: "Read-only copilot over Shopify + vault",
  },
  {
    href: "/agents",
    label: "Agents",
    icon: Bot,
    description: "Templates and configuration",
  },
  {
    href: "/flows",
    label: "Flows",
    icon: Workflow,
    description: "Configure CS flows (your SOPs)",
  },
  {
    href: "/cs",
    label: "Customer Service",
    icon: LifeBuoy,
    description: "Tickets, escalation, approvals",
  },
  {
    href: "/brand",
    label: "Brand",
    icon: BookOpen,
    description: "Markdown vault the agents read",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
    description: "Connections, team, branding, runtime",
  },
];
