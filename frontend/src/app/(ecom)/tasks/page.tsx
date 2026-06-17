import { SlicePlaceholder } from "@/components/ecom/SlicePlaceholder";

export default function TasksPage() {
  return (
    <SlicePlaceholder
      title="Tasks"
      subtitle="Per-person Kanban for the team"
      slice="Build slice 4"
      bullets={[
        "Reshapes the existing boards/tasks models into a per-person Kanban.",
        "Cards assigned to team members with drag-and-drop lanes.",
        "Today's tasks summary surfaces on Overview.",
      ]}
    />
  );
}
