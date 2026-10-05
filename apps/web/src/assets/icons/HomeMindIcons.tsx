import type { ReactNode, SVGProps } from "react";
import { cn } from "@/utils/cn";

type IconProps = SVGProps<SVGSVGElement>;

function base(
  className: string | undefined,
  props: IconProps,
  paths: ReactNode,
) {
  return (
    <svg
      className={cn("h-5 w-5 shrink-0", className)}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths}
    </svg>
  );
}

export function MicIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z" />
      <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
      <path d="M12 18v3" />
    </>,
  );
}

export function BotIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <rect x="5" y="8" width="14" height="10" rx="3" />
      <path d="M12 4v4" />
      <circle cx="12" cy="4" r="1" fill="currentColor" stroke="none" />
      <circle cx="9" cy="13" r="1" fill="currentColor" stroke="none" />
      <circle cx="15" cy="13" r="1" fill="currentColor" stroke="none" />
      <path d="M5 13H3.5a1.5 1.5 0 0 1 0-3H5" />
      <path d="M19 13h1.5a1.5 1.5 0 0 0 0-3H19" />
    </>,
  );
}

export function BulbIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M9 18h6" />
      <path d="M10 21h4" />
      <path d="M12 3a6 6 0 0 0-4 10c.6.6 1 1.4 1 2.2V16h6v-.8c0-.8.4-1.6 1-2.2A6 6 0 0 0 12 3z" />
    </>,
  );
}

export function SnowflakeIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 2v20" />
      <path d="m4.9 7 14.2 10" />
      <path d="m19.1 7-14.2 10" />
      <path d="m8 4 4 3 4-3" />
      <path d="m8 20 4-3 4 3" />
    </>,
  );
}

export function LockIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>,
  );
}

export function CurtainIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M4 4h16" />
      <path d="M6 4v16" />
      <path d="M18 4v16" />
      <path d="M6 8c2 2 4 2 6 0" />
      <path d="M12 8c2 2 4 2 6 0" />
    </>,
  );
}

export function MusicIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </>,
  );
}

export function ShieldLockIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 3 5 6v5c0 4.5 2.9 7.8 7 9 4.1-1.2 7-4.5 7-9V6l-7-3z" />
      <rect x="10" y="11" width="4" height="3.5" rx="0.5" />
      <path d="M11 11V9.5a1 1 0 0 1 2 0V11" />
    </>,
  );
}

export function CheckIcon({ className, ...props }: IconProps) {
  return base(className, props, <path d="M5 13l4 4L19 7" />);
}

export function HelpCircleIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4" />
      <path d="M12 17h.01" />
    </>,
  );
}

export function AlertTriangleIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </>,
  );
}

export function PlusIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>,
  );
}

export function ChevronRightIcon({ className, ...props }: IconProps) {
  return base(className, props, <path d="M9 6l6 6-6 6" />);
}

export function ChevronDownIcon({ className, ...props }: IconProps) {
  return base(className, props, <path d="M6 9l6 6 6-6" />);
}

export function SpeakerIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <rect x="4" y="3" width="8" height="18" rx="2" />
      <circle cx="8" cy="14" r="2.5" />
      <path d="M15 8a5 5 0 0 1 0 8" />
      <path d="M17.5 5.5a9 9 0 0 1 0 13" />
    </>,
  );
}

export function TvIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <rect x="3" y="5" width="18" height="12" rx="2" />
      <path d="M8 21h8" />
      <path d="M12 17v4" />
    </>,
  );
}

export function FanIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <circle cx="12" cy="12" r="2" />
      <path d="M12 4c2 2 2 4 0 6-2-2-2-4 0-6z" />
      <path d="M20 12c-2 2-4 2-6 0 2-2 4-2 6 0z" />
      <path d="M12 20c-2-2-2-4 0-6 2 2 2 4 0 6z" />
      <path d="M4 12c2-2 4-2 6 0-2 2-4 2-6 0z" />
    </>,
  );
}

export function PlugIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M9 3v6" />
      <path d="M15 3v6" />
      <path d="M7 9h10v3a5 5 0 0 1-10 0V9z" />
      <path d="M12 17v4" />
    </>,
  );
}

export function CameraIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M4 8h3l2-2h6l2 2h3v11H4V8z" />
      <circle cx="12" cy="13" r="3" />
    </>,
  );
}

export function DropletIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 3s6 6.5 6 10a6 6 0 1 1-12 0c0-3.5 6-10 6-10z" />
    </>,
  );
}

export function FlameIcon({ className, ...props }: IconProps) {
  return base(
    className,
    props,
    <>
      <path d="M12 3c2 4-1 6 1 9 1.2 1.8 3 2.4 3 5a4 4 0 1 1-8 0c0-2.2 1-3.8 2.4-5.4C12.2 9.8 10 7.8 12 3z" />
    </>,
  );
}
