"use client";

import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Chat() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const q = input.trim();
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/query?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: "Error: " + (err as Error).message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 pb-32">
        {messages.length === 0 ? (
          <div className="h-[70vh] flex flex-col items-center justify-center">
            <h1 className="text-4xl font-light mb-2">Chat</h1>
            <p className="text-gray-500">Ask about FEC contributions in 2025</p>
          </div>
        ) : (
          <div className="pt-8 space-y-6">
            {messages.map((m, i) => (
              <div key={i}>
                <p className="text-sm font-bold uppercase tracking-wide mb-2" style={{ color: m.role === "user" ? "#666" : "var(--primary)" }}>
                  {m.role === "user" ? "You" : "Chat"}
                </p>
                {m.role === "assistant" ? (
                  <Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown>
                ) : (
                  <p>{m.content}</p>
                )}
              </div>
            ))}
            {loading && (
              <div>
                <p className="text-sm font-bold uppercase tracking-wide mb-2" style={{ color: "var(--primary)" }}>Chat</p>
                <p className="text-gray-400">Thinking...</p>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="fixed bottom-0 inset-x-0 bg-white border-t border-gray-100 p-4">
        <form onSubmit={submit} className="max-w-3xl mx-auto flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type here"
            disabled={loading}
            className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:border-gray-300"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="text-white rounded-lg px-4 py-3 disabled:opacity-40"
            style={{ backgroundColor: "var(--primary)" }}
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}
