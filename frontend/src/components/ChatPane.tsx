"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, AlertCircle, BookOpen } from "lucide-react";
import { Citation } from "../lib/api";

export interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: Citation[];
  isEmergency?: boolean;
  isStreaming?: boolean;
}

interface ChatPaneProps {
  messages: MessageItem[];
  onSendMessage: (text: string) => void;
  isProcessing: boolean;
}

const QUICK_PROMPTS = [
  { label: "Reschedule to Friday", prompt: "Please reschedule my screening colonoscopy to Friday October 16 at 2:00 PM." },
  { label: "Split-dose PEG timing", prompt: "When exactly do I drink the first and second doses of my PEG bowel prep?" },
  { label: "Lantus / insulin dose", prompt: "I take 24 units of Lantus every night. How should I adjust it the night before my colonoscopy?" },
  { label: "Can I eat red Jell-O?", prompt: "Can I eat cherry red Jell-O during my clear liquid diet?" },
  { label: "Blood thinner (Eliquis)", prompt: "How many days before my colonoscopy do I need to hold Eliquis?" },
  { label: "Emergency red-flag", prompt: "I am having severe bleeding with large blood clots filling the toilet!" },
];

export const ChatPane: React.FC<ChatPaneProps> = ({
  messages,
  onSendMessage,
  isProcessing,
}) => {
  const [input, setInput] = useState("");
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleChipClick = (prompt: string) => {
    if (isProcessing) return;
    onSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-full rounded-[12px] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      {/* Pane header */}
      <div className="h-12 px-4 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--accent)]" />
          <h2 className="text-[13px] font-medium text-[var(--text)]">
            Patient communication
          </h2>
        </div>
        <span className="text-[12px] text-[var(--text-muted)]">
          HIPAA masking active
        </span>
      </div>

      {/* Quick action chips */}
      <div className="px-3 py-2 bg-[var(--subtle)] border-b border-[var(--border)] flex items-center gap-2 overflow-x-auto shrink-0">
        <span className="text-[12px] font-medium text-[var(--text-muted)] shrink-0">
          Suggestions:
        </span>
        {QUICK_PROMPTS.map((qp, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleChipClick(qp.prompt)}
            disabled={isProcessing}
            className="btn-base btn-secondary h-7 px-2.5 text-[12px] rounded-[8px] whitespace-nowrap shrink-0 disabled:opacity-40"
          >
            {qp.label}
          </button>
        ))}
      </div>

      {/* Messages stream */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
        aria-live="polite"
        aria-atomic="false"
      >
        {messages.map((m) => {
          const isUser = m.role === "user";
          return (
            <div
              key={m.id}
              className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
            >
              <div className="flex items-center gap-2 mb-1 px-1">
                <span className="text-[12px] font-medium text-[var(--text-muted)]">
                  {isUser ? "You" : "Clinical assistant"}
                </span>
                <span className="text-[12px] text-[var(--text-muted)]">
                  {m.timestamp}
                </span>
              </div>

              <div
                className={`rounded-[8px] p-3 text-[14px] leading-relaxed prose-text ${
                  isUser
                    ? "bg-[var(--subtle)] border border-[var(--border)] text-[var(--text)]"
                    : m.isEmergency
                    ? "bg-[var(--danger-subtle)] border border-[var(--danger)] text-[var(--text)]"
                    : "bg-[var(--surface)] border border-[var(--border)] text-[var(--text)]"
                }`}
              >
                {/* Emergency banner */}
                {m.isEmergency && (
                  <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--danger)] mb-2 pb-1 border-b border-[var(--danger)]/30">
                    <AlertCircle className="w-4 h-4 stroke-[1.5]" />
                    <span>Clinical escalation notice</span>
                  </div>
                )}

                <div>
                  {m.isStreaming ? (
                    <span className="animate-settle">{m.content}</span>
                  ) : (
                    m.content
                  )}
                  {m.isStreaming && (
                    <span className="inline-block w-1.5 h-3.5 ml-1 bg-[var(--accent)] align-middle animate-pulse" />
                  )}
                </div>

                {/* Source citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-[var(--border)] space-y-1.5">
                    <div className="text-[12px] font-medium text-[var(--text-muted)] flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 stroke-[1.5] text-[var(--text-muted)]" />
                      <span>Clinical sources</span>
                    </div>
                    {m.citations.map((c, cIdx) => (
                      <div
                        key={cIdx}
                        className="rounded-[8px] p-2 bg-[var(--subtle)] border border-[var(--border)] text-[12px]"
                      >
                        <div className="font-medium text-[var(--text)]">{c.source_document}</div>
                        <div className="text-[var(--text-muted)]">{c.source_section}</div>
                        <div className="text-[var(--text)] mt-1 italic line-clamp-2">
                          &ldquo;{c.text_snippet}&rdquo;
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Processing state indicator */}
        {isProcessing && messages[messages.length - 1]?.role === "user" && (
          <div className="flex items-center gap-2 text-[12px] text-[var(--text-muted)] px-1 py-2">
            <span className="w-1.5 h-1.5 rounded-[8px] bg-[var(--accent)] animate-pulse" />
            <span>Verifying against clinical EHR and guidelines...</span>
          </div>
        )}
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-[var(--border)] bg-[var(--surface)]">
        <label htmlFor="chat-input" className="text-[13px] font-medium text-[var(--text-muted)] mb-1.5 block">
          Ask a question or request an appointment change
        </label>
        <div className="flex items-center gap-2">
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            placeholder="Type your message..."
            className="input-base flex-1"
          />
          {/* THE SINGLE PRIMARY BUTTON OF THE VIEW */}
          <button
            type="submit"
            disabled={isProcessing || !input.trim()}
            aria-label="Send message"
            className="btn-base btn-primary h-10 px-4 disabled:opacity-40"
          >
            <Send className="w-4 h-4 stroke-[1.5]" />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
};


