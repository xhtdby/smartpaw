"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { sendChatMessage, type ChatMessage, type ChatResponse } from "@/lib/api";
import { useLanguage, LanguageSelector } from "@/lib/language";

const STORAGE_KEY = "smartpaw-chat-history";
const ANALYSIS_KEY = "smartpaw-analysis-context";

function ChatInner() {
  const { language, t } = useLanguage();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysisContext, setAnalysisContext] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  // Load history + analysis context on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) setMessages(JSON.parse(saved));
    } catch { /* ignore */ }
    const ctx = localStorage.getItem(ANALYSIS_KEY);
    if (ctx) setAnalysisContext(ctx);
    // Auto-send context message if coming from analysis
    if (searchParams.get("from") === "analysis" && ctx) {
      const autoMsg = `I just analyzed a dog photo. Here's what was found:\n${ctx}\n\nWhat should I do next?`;
      setInput(autoMsg);
    }
  }, [searchParams]);

  // Save history
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50)));
    }
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data: ChatResponse = await sendChatMessage(text, language, messages, analysisContext);
      const assistantMsg: ChatMessage = { role: "assistant", content: data.response };
      setMessages((prev) => [...prev, assistantMsg]);
      if (data.sources?.length) setSources(data.sources);
      // Clear analysis context after first use
      if (analysisContext) {
        setAnalysisContext(undefined);
        localStorage.removeItem(ANALYSIS_KEY);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm sorry, I'm having trouble connecting right now. For immediate help, please call the AWBI helpline at 1962.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    setMessages([]);
    setSources([]);
    localStorage.removeItem(STORAGE_KEY);
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
            <button onClick={clearHistory} className="text-xs text-gray-400 hover:text-red-500" title="Clear chat">
              🗑️
            </button>
          )}
          <LanguageSelector compact />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
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
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl p-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[var(--color-warm-500)] text-white rounded-br-md"
                  : "bg-white border border-gray-100 text-gray-700 rounded-bl-md shadow-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Sources */}
        {sources.length > 0 && messages.length > 0 && (
          <div className="text-xs text-gray-400 px-2">
            Sources: {sources.join(", ")}
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
