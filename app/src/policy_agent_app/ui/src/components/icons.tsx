import type { ReactNode } from "react";

/** Small inline SVG icon set — keeps the UI dependency-free. */
type IconProps = { className?: string; size?: number };

function svg(path: ReactNode) {
  return ({ className, size = 18 }: IconProps) => (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {path}
    </svg>
  );
}

export const PolicyIcon = svg(
  <>
    <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" />
    <path d="M9 12l2 2 4-4" />
  </>,
);
export const ApprovalIcon = svg(
  <>
    <path d="M9 11l3 3L22 4" />
    <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
  </>,
);
export const ScanIcon = svg(
  <>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.35-4.35" />
  </>,
);
export const RemediationIcon = svg(
  <>
    <path d="M14.7 6.3a4 4 0 00-5.6 5.6l-6 6a1.5 1.5 0 002 2l6-6a4 4 0 005.6-5.6l-2.4 2.4-2-2 2.4-2.4z" />
  </>,
);
export const SettingsIcon = svg(
  <>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-2.9 1.31V21a2 2 0 01-4 0v-.09A1.65 1.65 0 007 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 003 15a1.65 1.65 0 00-1.51-1H1a2 2 0 010-4h.09A1.65 1.65 0 003 8.6a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 007 4.6h.09A1.65 1.65 0 009 3.09V3a2 2 0 014 0v.09A1.65 1.65 0 0016 4.6a1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0021 9v.09a2 2 0 010 4z" />
  </>,
);
export const ChevronIcon = svg(<path d="M6 9l6 6 6-6" />);
export const LightbulbIcon = svg(
  <>
    <path d="M9 18h6M10 22h4" />
    <path d="M12 2a7 7 0 00-4 12.7c.6.5 1 1.3 1 2.1V17h6v-.2c0-.8.4-1.6 1-2.1A7 7 0 0012 2z" />
  </>,
);
export const UserIcon = svg(
  <>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0116 0" />
  </>,
);
export const SunIcon = svg(
  <>
    <circle cx="12" cy="12" r="4.5" />
    <path d="M12 1.5v2.5M12 20v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M1.5 12h2.5M20 12h2.5M4.2 19.8l1.8-1.8M18 6l1.8-1.8" />
  </>,
);
export const MoonIcon = svg(<path d="M20 14.5A8 8 0 019.5 4a7 7 0 100 16 8 8 0 0010.5-5.5z" />);
export const CheckIcon = svg(<path d="M20 6L9 17l-5-5" />);
export const XIcon = svg(<path d="M18 6L6 18M6 6l12 12" />);
export const PlusIcon = svg(<path d="M12 5v14M5 12h14" />);
export const TrashIcon = svg(
  <>
    <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
  </>,
);
export const ArrowLeftIcon = svg(<path d="M19 12H5M12 19l-7-7 7-7" />);
export const PlayIcon = svg(<path d="M6 4l14 8-14 8V4z" />);
export const CalendarIcon = svg(
  <>
    <rect x="3" y="4" width="18" height="17" rx="2" />
    <path d="M3 9h18M8 2v4M16 2v4" />
  </>,
);
export const UploadIcon = svg(
  <>
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
    <path d="M17 8l-5-5-5 5M12 3v13" />
  </>,
);
export const AssignIcon = svg(
  <>
    <circle cx="9" cy="8" r="4" />
    <path d="M3 21a6 6 0 0112 0M17 8v6M20 11h-6" />
  </>,
);
export const ExternalIcon = svg(
  <>
    <path d="M14 4h6v6M20 4l-9 9M18 13v6a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h6" />
  </>,
);
export const ListIcon = svg(
  <>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </>,
);
export const CodeIcon = svg(<path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />);
export const SendIcon = svg(<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />);
export const ArchiveIcon = svg(
  <>
    <path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4" />
  </>,
);
export const EditIcon = svg(
  <>
    <path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
  </>,
);
export const SparkleIcon = svg(
  <>
    <path d="M12 3l1.8 4.9L19 9.7l-4.4 2.4L13 17l-1-4.9L7 9.7l4.9-1.4L12 3z" />
    <path d="M5 15l.7 1.9L8 17.6l-1.8.9L5 20.5l-.6-2L2.6 17.6 4.4 17 5 15z" />
  </>,
);
export const ClockIcon = svg(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </>,
);
export const ChatIcon = svg(
  <path d="M21 11.5a8.5 8.5 0 01-12.3 7.6L3 21l1.9-5.7A8.5 8.5 0 1121 11.5z" />,
);
