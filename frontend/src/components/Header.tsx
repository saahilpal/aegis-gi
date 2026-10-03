"use client";

import React, { useEffect, useState } from "react";
import { RefreshCw, BarChart2, Sun, Moon } from "lucide-react";

interface HeaderProps {
  onRunDemo: (demoNumber: 1 | 2 | 3) => void;
  onOpenEvalModal: () => void;
  onResetEhr: () => void;
  isProcessing: boolean;
  activePatient: string;
}

export const Header: React.FC<HeaderProps> = ({
  onRunDemo,
  onOpenEvalModal,
  onResetEhr,
  isProcessing,
  activePatient,
}) => {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const existing =
        (document.documentElement.getAttribute("data-theme") as "light" | "dark") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      setTheme(existing);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    if (next === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("aegis_theme", next);
    } catch {
      // Ignore storage errors in restricted contexts
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-[var(--border)] bg-[var(--surface)] transition-colors">
      <div className="max-w-[1100px] w-full mx-auto px-3 sm:px-4 h-14 flex items-center justify-between gap-2 sm:gap-3">
        {/* Brand & patient context */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 whitespace-nowrap">
          <span className="text-[14px] font-semibold tracking-[-0.02em] text-[var(--text)] whitespace-nowrap">
            Aegis GI
          </span>
          <span className="text-[12px] text-[var(--text-muted)] bg-[var(--subtle)] border border-[var(--border)] px-2 py-0.5 rounded-[8px] whitespace-nowrap hidden sm:inline">
            Outcome-verified
          </span>
          <span className="text-[var(--border)] hidden lg:inline">|</span>
          <span className="text-[12px] text-[var(--text-muted)] hidden lg:inline whitespace-nowrap">
            Patient: <strong className="font-medium text-[var(--text)]">{activePatient}</strong>
          </span>
        </div>

        {/* Action controls (secondary buttons - exactly one primary is reserved for send) */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <button
            type="button"
            onClick={() => onRunDemo(1)}
            disabled={isProcessing}
            title="Demo 1: Successful appointment reschedule"
            className="btn-base btn-secondary h-8 sm:h-9 px-2 sm:px-3 text-[12px] rounded-[8px] whitespace-nowrap shrink-0 disabled:opacity-40"
          >
            <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--text)]" />
            <span className="sm:hidden">D1</span>
            <span className="hidden sm:inline">Reschedule</span>
          </button>

          <button
            type="button"
            onClick={() => onRunDemo(2)}
            disabled={isProcessing}
            title="Demo 2: Tool failure handled truthfully"
            className="btn-base btn-secondary h-8 sm:h-9 px-2 sm:px-3 text-[12px] rounded-[8px] whitespace-nowrap shrink-0 disabled:opacity-40"
          >
            <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--text-muted)]" />
            <span className="sm:hidden">D2</span>
            <span className="hidden sm:inline">Failure</span>
          </button>

          <button
            type="button"
            onClick={() => onRunDemo(3)}
            disabled={isProcessing}
            title="Hero Demo 3: Forced failure with false resolution caught by verifier"
            className="btn-base btn-secondary h-8 sm:h-9 px-2 sm:px-3 text-[12px] rounded-[8px] whitespace-nowrap shrink-0 disabled:opacity-40"
          >
            <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--danger)]" />
            <span className="sm:hidden">D3</span>
            <span className="hidden sm:inline">False res</span>
          </button>

          <button
            type="button"
            onClick={onOpenEvalModal}
            title="Open 36-scenario benchmark suite"
            aria-label="Open benchmark suite"
            className="btn-base btn-secondary h-8 sm:h-9 px-2 sm:px-3 text-[12px] rounded-[8px] whitespace-nowrap shrink-0"
          >
            <BarChart2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--text-muted)] stroke-[1.5]" />
            <span className="hidden md:inline">Benchmark</span>
          </button>

          <button
            type="button"
            onClick={onResetEhr}
            disabled={isProcessing}
            title="Reset clinical EHR state"
            aria-label="Reset clinical EHR"
            className="btn-base btn-ghost h-8 w-8 sm:h-9 sm:w-9 p-0 rounded-[8px] text-[var(--text-muted)] hover:text-[var(--text)] shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4 stroke-[1.5]" />
          </button>

          <button
            type="button"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="btn-base btn-ghost h-8 w-8 sm:h-9 sm:w-9 p-0 rounded-[8px] text-[var(--text-muted)] hover:text-[var(--text)] shrink-0"
          >
            {theme === "dark" ? (
              <Sun className="w-3.5 h-3.5 sm:w-4 sm:h-4 stroke-[1.5]" />
            ) : (
              <Moon className="w-3.5 h-3.5 sm:w-4 sm:h-4 stroke-[1.5]" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};


