import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Send, X, Loader2, AlertCircle } from "lucide-react";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useAuthUI } from "@/context/AuthUIContext";
import { toast } from "sonner";

export default function AIBuddyWidget() {
  const { user } = useAuth();
  const { openAuth } = useAuthUI();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const scrollRef = useRef(null);

  const isAuthed = user && typeof user === "object";

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading, open]);

  useEffect(() => {
    if (!open || !isAuthed) return;

    let cancelled = false;
    const load = async () => {
      try {
        const [{ data: statusData }, { data: historyData }] = await Promise.all([
          api.get("/ai/status"),
          api.get("/ai/history"),
        ]);
        if (cancelled) return;
        setStatus(statusData);
        const history = historyData.messages || [];
        if (history.length) {
          setMessages(history.map((m) => ({ role: m.role, content: m.message })));
        } else {
          setMessages([
            {
              role: "assistant",
              content:
                "Hey — I'm your FitCheck Coach. Tell me your goal or ask me anything about training, recovery, nutrition, or exercise technique.",
            },
          ]);
        }
      } catch (e) {
        if (!cancelled) {
          setStatus({ configured: false });
          setMessages([
            {
              role: "assistant",
              content: "I couldn't connect to the FitCheck AI service. Try again after the backend is redeployed.",
              error: true,
            },
          ]);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [open, isAuthed]);

  const openWidget = () => {
    if (!isAuthed) {
      openAuth("signup");
      return;
    }
    setOpen(true);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai/chat", {
        message: text,
        session_id: sessionId,
      });
      setSessionId(data.session_id);
      setStatus((s) => ({ ...(s || {}), configured: true }));
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
    } catch (e) {
      const message = formatApiErrorDetail(e.response?.data?.detail) || e.message || "AI Buddy could not respond.";
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: message,
          error: true,
        },
      ]);
      toast.error(message);
      setInput(text);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.8, duration: 0.4 }}
        onClick={openWidget}
        className="fixed bottom-20 right-6 z-40 group inline-flex items-center gap-2 pl-4 pr-5 py-3 rounded-full bg-[#39FF14] text-black font-semibold shadow-[0_0_24px_rgba(57,255,20,0.35)] hover:shadow-[0_0_48px_rgba(57,255,20,0.65)] hover:-translate-y-0.5 transition-all duration-300"
        data-testid="ai-buddy-launcher"
        aria-label="Open AI Buddy"
      >
        <span className="relative flex w-2.5 h-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-60" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black" />
        </span>
        <Bot size={16} strokeWidth={2.5} />
        <span className="text-sm">AI Buddy</span>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end md:items-center justify-center p-0 md:p-6"
            onClick={() => setOpen(false)}
            data-testid="ai-buddy-overlay"
          >
            <motion.div
              initial={{ y: 40, opacity: 0, scale: 0.98 }}
              animate={{ y: 0, opacity: 1, scale: 1 }}
              exit={{ y: 40, opacity: 0, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 260, damping: 28 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[#0A0A0A] border border-zinc-800 rounded-t-2xl md:rounded-2xl w-full md:max-w-xl h-[85vh] md:h-[640px] flex flex-col shadow-2xl shadow-black overflow-hidden"
              data-testid="ai-buddy-panel"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-900">
                <div className="flex items-center gap-3">
                  <span className="w-9 h-9 rounded-xl bg-black border border-[#39FF14]/40 flex items-center justify-center text-[#39FF14]">
                    <Bot size={16} />
                  </span>
                  <div>
                    <div className="font-heading text-sm font-semibold text-white">FitCheck Coach</div>
                    <div className="text-[11px] text-zinc-500 flex items-center gap-1.5">
                      <span className={`inline-block w-1.5 h-1.5 rounded-full ${status?.configured ? "bg-[#39FF14] animate-pulse" : "bg-red-500"}`} />
                      {status?.configured ? `AI coach · ${status.model || "online"}` : "AI setup required"}
                    </div>
                  </div>
                </div>
                <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white transition-colors" aria-label="Close AI Buddy" data-testid="ai-buddy-close">
                  <X size={18} />
                </button>
              </div>

              {!status?.configured && status !== null && (
                <div className="mx-5 mt-4 flex gap-2 rounded-xl border border-amber-900/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-200" data-testid="ai-buddy-config-warning">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>Add <b>EMERGENT_LLM_KEY</b> to the backend environment, then redeploy the backend.</span>
                </div>
              )}

              <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5 space-y-4" data-testid="ai-buddy-messages">
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${m.role === "user" ? "bg-[#39FF14] text-black rounded-br-md" : m.error ? "bg-red-950/30 text-red-200 border border-red-900/50 rounded-bl-md" : "bg-zinc-900 text-zinc-100 border border-zinc-800 rounded-bl-md"}`}>
                      {m.content}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-zinc-400 inline-flex items-center gap-2">
                      <Loader2 size={14} className="animate-spin text-[#39FF14]" />
                      Coach is thinking…
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t border-zinc-900 p-3 flex items-end gap-2 bg-black">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKeyDown}
                  rows={1}
                  placeholder="Ask anything — training, recovery, nutrition…"
                  className="flex-1 resize-none max-h-32 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                  data-testid="ai-buddy-input"
                />
                <button
                  onClick={send}
                  disabled={loading || !input.trim()}
                  className="w-11 h-11 shrink-0 rounded-xl bg-[#39FF14] text-black flex items-center justify-center hover:bg-[#32E612] disabled:opacity-40 transition-colors"
                  aria-label="Send"
                  data-testid="ai-buddy-send"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
