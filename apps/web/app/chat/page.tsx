"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { apiGet, type ChatEvent } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import {
  ModelToggle,
  isHeavyCpuModel,
  pickModel,
  readStoredModel,
  writeStoredModel,
  type OllamaModel,
} from "@/lib/model-select";

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  model?: string;
  sources?: { filename: string; chunk_index: number }[];
};

export default function ChatPage() {
  const { t, locale } = useI18n();
  const [model, setModel] = useState("");
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages((current) => {
      const welcome = { role: "assistant" as const, content: t("chat.welcome") };
      if (current.length === 0) {
        return [welcome];
      }
      if (current.length === 1 && current[0].role === "assistant" && !current[0].agent) {
        return [welcome];
      }
      return current;
    });
  }, [locale, t]);

  useEffect(() => {
    apiGet<{ default: string; models: OllamaModel[] }>("/models")
      .then((payload) => {
        const catalog = (payload.models || []).filter((item) => item?.name);
        setModels(catalog);
        const chosen = pickModel(
          catalog.map((item) => item.name),
          payload.default,
          readStoredModel(),
        );
        setModel(chosen);
        if (chosen) {
          writeStoredModel(chosen);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) {
      return;
    }
    setInput("");
    setBusy(true);
    setMessages((current) => [
      ...current,
      { role: "user", content: question },
      { role: "assistant", content: "", sources: [], model: model || undefined },
    ]);

    try {
      const response = await fetch("/api/runtime/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: question, model: model || undefined }),
      });
      if (!response.ok || !response.body) {
        throw new Error(`${t("chat.failed")} (${response.status})`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.split("\n").find((item) => item.startsWith("data: "));
          if (!line) {
            continue;
          }
          const event = JSON.parse(line.slice(6)) as ChatEvent;
          setMessages((current) => {
            const next = [...current];
            const last = { ...next[next.length - 1] };
            if (event.type === "token") {
              last.content += event.content;
            }
            if (event.type === "route") {
              last.agent = event.name || event.agent;
            }
            if (event.type === "model") {
              last.model = event.name;
            }
            if (event.type === "sources") {
              last.sources = event.items;
            }
            if (event.type === "error") {
              last.content = last.content || event.message;
            }
            next[next.length - 1] = last;
            return next;
          });
        }
      }
    } catch (err) {
      setMessages((current) => {
        const next = [...current];
        next[next.length - 1] = {
          role: "assistant",
          content: err instanceof Error ? err.message : t("chat.failed"),
        };
        return next;
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1 suppressHydrationWarning>{t("chat.title")}</h1>
          <p suppressHydrationWarning>{t("chat.lead")}</p>
        </div>
        <ModelToggle models={models} value={model} onChange={setModel} label={t("chat.model")} />
      </div>
      {isHeavyCpuModel(model) ? <p className="muted">{t("chat.cpuHint")}</p> : null}
      <div className="chat-wrap">
        <div className="messages">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`}>
              {message.role === "assistant" && (message.agent || message.model) ? (
                <div className="sources">
                  {message.agent ? <span className="source">{message.agent}</span> : null}
                  {message.model ? <span className="source">{message.model}</span> : null}
                </div>
              ) : null}
              {message.role === "assistant" && message.sources?.length ? (
                <div className="sources">
                  {message.sources.map((source) => (
                    <span className="source" key={`${source.filename}-${source.chunk_index}`}>
                      {t("chat.source", { filename: source.filename, index: source.chunk_index })}
                    </span>
                  ))}
                </div>
              ) : null}
              <div className={`bubble ${message.role}`}>
                {message.content
                  || (busy && index === messages.length - 1
                    ? t("chat.writing", { model: message.model || model || "Ollama" })
                    : "")}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form className="composer" onSubmit={onSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={t("chat.placeholder")}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button className="btn" disabled={busy || !input.trim()}>
            {t("chat.send")}
          </button>
        </form>
      </div>
    </>
  );
}
