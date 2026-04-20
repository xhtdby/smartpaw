"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { sendChatMessage, type ChatMessage } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState("en");
  const bottomRef = useRef<HTMLDivElement>(null);

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
      const data = await sendChatMessage(text, language, messages);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I'm sorry, I'm having trouble connecting right now. For immediate help, please call the AWBI helpline at 1962.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 bg-white sticky top-0 z-10">
        <Link href="/" className="text-2xl">
          ←
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-[var(--color-warm-700)]">
            🐾 SmartPaw Chat
          </h1>
          <p className="text-xs text-gray-400">
            Ask about dog first aid &amp; care
          </p>
        </div>
        <div className="flex gap-1">
          {[
            { code: "en", label: "EN" },
            { code: "hi", label: "हि" },
            { code: "mr", label: "म" },
          ].map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`w-8 h-8 rounded-full text-xs font-bold ${
                language === l.code
                  ? "bg-[var(--color-warm-500)] text-white"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="text-5xl mb-4">🐾</div>
            <h2 className="text-lg font-semibold text-[var(--color-warm-700)] mb-2">
              Hi, I&apos;m SmartPaw!
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              I can help you with first aid for stray dogs, understanding dog
              behavior, and finding resources in Mumbai.
            </p>
            <div className="space-y-2">
              {[
                "How do I help a dog with mange?",
                "What should I do if I find injured puppies?",
                "Is it safe to approach a growling dog?",
                "What are the signs of rabies?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                  }}
                  className="block w-full bg-white border border-gray-200 rounded-lg p-3 text-left text-sm text-gray-600 hover:bg-[var(--color-warm-50)] hover:border-[var(--color-warm-300)]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
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

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-md p-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
                <span
                  className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <span
                  className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
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
            placeholder="Ask about dog care or first aid..."
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
        <p className="text-center text-xs text-gray-300 mt-2">
          Not a vet. Always consult a professional for serious cases.
        </p>
      </div>
    </main>
  );
}
