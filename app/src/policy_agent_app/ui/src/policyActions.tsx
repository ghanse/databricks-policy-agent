import type { ToastKind } from "./toast";
import { ArchiveIcon, CheckIcon, SendIcon, XIcon } from "./components/icons";

type IconType = (props: { className?: string; size?: number }) => JSX.Element;

export type ActionColor = "ok" | "danger" | "neutral" | "accent";

export interface TransitionSpec {
  action: string;
  label: string;
  icon: IconType;
  kind: ToastKind;
  color: ActionColor;
}

/** Approval-workflow transitions available from each policy status. */
export const TRANSITIONS: Record<string, TransitionSpec[]> = {
  draft: [{ action: "submit", label: "Submit for review", icon: SendIcon, kind: "save", color: "accent" }],
  rejected: [{ action: "submit", label: "Resubmit for review", icon: SendIcon, kind: "save", color: "accent" }],
  in_review: [
    { action: "approve", label: "Approve", icon: CheckIcon, kind: "save", color: "ok" },
    { action: "reject", label: "Reject", icon: XIcon, kind: "delete", color: "danger" },
  ],
  approved: [{ action: "archive", label: "Archive", icon: ArchiveIcon, kind: "delete", color: "neutral" }],
};

export function transitionsFor(status: string): TransitionSpec[] {
  return TRANSITIONS[status] ?? [];
}
