"use client";

import { useState, useRef, useEffect, Suspense, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { sendChatMessage, type ChatMessage, type ChatResponse, type ActionCard } from "@/lib/api";
import { useLanguage, LanguageSelector } from "@/lib/language";

const STORAGE_KEY = "indieaid-chat-history";
const LEGACY_STORAGE_KEY = "smartpaw-chat-history";
const ANALYSIS_KEY = "indieaid-analysis-context";
const LEGACY_ANALYSIS_KEY = "smartpaw-analysis-context";

// ---------------------------------------------------------------------------
// Lightweight markdown renderer — covers bold, italic, headings, lists, hr
// ---------------------------------------------------------------------------
function renderMarkdown(text: string): ReactNode[] {
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = (key: string) => {
    if (listItems.length === 0) return;
    if (listType === "ol") {
      nodes.push(
        <ol key={key} className="list-decimal ml-5 space-y-0.5 my-1">
          {listItems.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ol>
      );
    } else {
      nodes.push(
        <ul key={key} className="list-disc ml-5 space-y-0.5 my-1">
          {listItems.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    }
    listItems = [];
    listType = null;
  };

  lines.forEach((line, idx) => {
    const olMatch = line.match(/^(\d+)\.\s+(.*)/);
    const ulMatch = line.match(/^[-*]\s+(.*)/);
    const h3Match = line.match(/^###\s+(.*)/);
    const h2Match = line.match(/^##\s+(.*)/);
    const h1Match = line.match(/^#\s+(.*)/);

    if (olMatch) {
      if (listType === "ul") flushList(`list-${idx}`);
      listType = "ol";
      listItems.push(olMatch[2]);
      return;
    }
    if (ulMatch) {
      if (listType === "ol") flushList(`list-${idx}`);
      listType = "ul";
      listItems.push(ulMatch[1]);
      return;
    }

    flushList(`list-${idx}`);

    if (line.trim() === "---" || line.trim() === "***") {
      nodes.push(<hr key={idx} className="border-gray-200 my-2" />);
      return;
    }
    if (h1Match) {
      nodes.push(<p key={idx} className="font-bold text-base mt-2 mb-0.5">{renderInline(h1Match[1])}</p>);
      return;
    }
    if (h2Match) {
      nodes.push(<p key={idx} className="font-semibold text-sm mt-2 mb-0.5">{renderInline(h2Match[1])}</p>);
      return;
    }
    if (h3Match) {
      nodes.push(<p key={idx} className="font-semibold text-sm mt-1">{renderInline(h3Match[1])}</p>);
      return;
    }
    if (line.trim() === "") {
      nodes.push(<div key={idx} className="h-1.5" />);
      return;
    }
    nodes.push(<p key={idx} className="leading-relaxed">{renderInline(line)}</p>);
  });

  flushList("list-final");
  return nodes;
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  // Bold+italic: ***text***
  // Bold: **text**
  // Italic: *text*
  const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[2]) parts.push(<strong key={key++}><em>{match[2]}</em></strong>);
    else if (match[3]) parts.push(<strong key={key++}>{match[3]}</strong>);
    else if (match[4]) parts.push(<em key={key++}>{match[4]}</em>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

// ---------------------------------------------------------------------------
// Action cards — Find Help / Learn / Emergency
// ---------------------------------------------------------------------------
function ActionCards({ cards }: { cards: ActionCard[] }) {
  if (!cards.length) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {cards.map((card, i) => {
        if (card.type === "emergency") {
          return (
            <Link
              key={i}
              href={card.href}
              className="flex items-center gap-1.5 bg-red-100 border border-red-300 text-red-700 text-xs font-semibold rounded-full px-3 py-1.5 hover:bg-red-200 transition-colors"
            >
              🚨 {card.label}
            </Link>
          );
        }
        if (card.type === "learn") {
          return (
            <Link
              key={i}
              href={card.href}
              className="flex items-center gap-1.5 bg-amber-50 border border-amber-300 text-amber-800 text-xs font-medium rounded-full px-3 py-1.5 hover:bg-amber-100 transition-colors"
            >
              📖 {card.label}
            </Link>
          );
        }
        // find_help
        return (
          <Link
            key={i}
            href={card.href}
            className="flex items-center gap-1.5 bg-[var(--color-warm-50)] border border-[var(--color-warm-300)] text-[var(--color-warm-700)] text-xs font-medium rounded-full px-3 py-1.5 hover:bg-[var(--color-warm-100)] transition-colors"
          >
            📍 {card.label}
          </Link>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Emergency banner — shown at top when last reply flagged is_emergency
// ---------------------------------------------------------------------------
function EmergencyBanner({ label }: { label: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-3 mb-3">
      <span className="text-xl shrink-0">🚨</span>
      <div>
        <p className="text-sm font-semibold text-red-700">{label}</p>
        <Link href="/nearby" className="text-xs text-red-600 underline mt-0.5 block">
          Open Find Help →
        </Link>
      </div>
    </div>
  );
}

// Attach action cards to messages for rendering
interface EnrichedMessage extends ChatMessage {
  action_cards?: ActionCard[];
  is_emergency?: boolean;
}

function ChatInner() {
  const { language, t } = useLanguage();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<EnrichedMessage[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysisContext, setAnalysisContext] = useState<string | undefined>();
  const [lastEmergency, setLastEmergency] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    try {
      const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
      if (saved) setMessages(JSON.parse(saved));
    } catch { /* ignore */ }
    const ctx = localStorage.getItem(ANALYSIS_KEY) || localStorage.getItem(LEGACY_ANALYSIS_KEY);
    if (ctx) setAnalysisContext(ctx);
    if (searchParams.get("from") === "analysis" && ctx) {
      const autoMsg = `I just analyzed a dog photo. Here's what was found:\n${ctx}\n\nWhat should I do next?`;
      setInput(autoMsg);
    }
  }, [searchParams]);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50)));
      localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: EnrichedMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data: ChatResponse = await sendChatMessage(text, language, messages, analysisContext);
      const assistantMsg: EnrichedMessage = {
        role: "assistant",
        content: data.response,
        action_cards: data.action_cards,
        is_emergency: data.is_emergency,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (data.sources?.length) setSources(data.sources);
      setLastEmergency(data.is_emergency ?? false);
      if (analysisContext) {
        setAnalysisContext(undefined);
        localStorage.removeItem(ANALYSIS_KEY);
        localStorage.removeItem(LEGACY_ANALYSIS_KEY);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: t("chat.error.network") },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    setMessages([]);
    setSources([]);
    setLastEmergency(false);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  };

  return (
    <main className="min-h-screen flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 bg-white sticky top-0 z-10">
        <Link href="/" className="text-2xl">←</Link>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-[var(--color-warm-700)] flex items-center gap-2">
            <Image src="/logo.png" alt="IndieAid" width={28} height={28} className="inline-block" />
            {t("chat.title")}
          </h1>
          <p className="text-xs text-gray-400">{t("chat.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button onClick={clearHistory} className="text-xs text-gray-400 hover:text-red-500" title={t("chat.action.clear")} aria-label={t("chat.action.clear")}>
              🗑️
            </button>
          )}
          <LanguageSelector compact />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">

        {/* Emergency banner — shown when last assistant message was emergency */}
        {lastEmergency && messages.length > 0 && (
          <EmergencyBanner label={t("chat.emergency.banner")} />
        )}

        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="text-5xl mb-4">🐾</div>
            <h2 className="text-lg font-semibold text-[var(--color-warm-700)] mb-2">
              {t("chat.welcome")}
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              {t("chat.welcome.desc")}
            </p>
            <div className="space-y-2">
              {(["chat.example.1", "chat.example.2", "chat.example.3", "chat.example.4"] as const).map((key) => {
                const q = t(key);
                return (
                  <button
                    key={key}
                    onClick={() => setInput(q)}
                    className="block w-full bg-white border border-gray-200 rounded-lg p-3 text-left text-sm text-gray-600 hover:bg-[var(--color-warm-50)] hover:border-[var(--color-warm-300)]"
                  >
                    {q}
                  </button>
                );
              })}
            </div>

            {/* Quick action links on welcome screen */}
            <div className="mt-6 flex flex-col gap-2">
              <Link href="/nearby" className="flex items-center justify-center gap-2 bg-[var(--color-warm-50)] border border-[var(--color-warm-200)] text-[var(--color-warm-700)] text-sm font-medium rounded-xl py-2.5 hover:bg-[var(--color-warm-100)]">
                📍 {t("chat.card.find_help")}
              </Link>
              <Link href="/learn" className="flex items-center justify-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 text-sm font-medium rounded-xl py-2.5 hover:bg-amber-100">
                📖 {t("chat.card.learn")}
              </Link>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] ${msg.role === "user" ? "" : "w-full"}`}>
              <div
                className={`rounded-2xl px-3.5 py-2.5 text-sm ${
                  msg.role === "user"
                    ? "bg-[var(--color-warm-500)] text-white rounded-br-md"
                    : "bg-white border border-gray-100 text-gray-700 rounded-bl-md shadow-sm"
                }`}
              >
                {msg.role === "assistant"
                  ? renderMarkdown(msg.content)
                  : msg.content}
              </div>
              {msg.role === "assistant" && msg.action_cards && msg.action_cards.length > 0 && (
                <ActionCards cards={msg.action_cards} />
              )}
            </div>
          </div>
        ))}

        {/* Sources */}
        {sources.length > 0 && messages.length > 0 && (
          <div className="text-xs text-gray-400 px-2">
            {t("chat.sources")}: {sources.join(", ")}
          </div>
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-md p-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="sticky bottom-0 bg-white border-t border-gray-100 p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={t("chat.placeholder")}
            className="flex-1 border border-gray-200 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:border-[var(--color-warm-400)]"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="bg-[var(--color-warm-500)] text-white rounded-full w-10 h-10 flex items-center justify-center disabled:opacity-50"
          >
            ↑
          </button>
        </div>
        <p className="text-center text-xs text-gray-300 mt-2">{t("disclaimer")}</p>
      </div>
    </main>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatInner />
    </Suspense>
  );
}
