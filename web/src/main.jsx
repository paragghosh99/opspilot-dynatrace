import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  BellRing,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Gauge,
  GitBranch,
  Loader2,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  Zap,
  X,
} from "lucide-react";
import "./styles.css";

const tabs = [
  { id: "problems", label: "Live", icon: Radio },
  { id: "history", label: "History", icon: Activity },
  { id: "mttr", label: "MTTR", icon: Gauge },
  { id: "runbook", label: "Runbook", icon: BrainCircuit },
];

const api = {
  problems: () => fetch("/api/problems").then((res) => res.json()),
  incidents: () => fetch("/api/incidents").then((res) => res.json()),
  runbook: () => fetch("/api/runbook").then((res) => res.json()),
  mttr: () => fetch("/api/mttr").then((res) => res.json()),
  poll: () => fetch("/poll", { method: "POST" }),
};

function severityTone(severity = "") {
  const value = severity.toLowerCase();
  if (value.includes("critical") || value.includes("availability")) return "from-rose-400 to-red-500 text-rose-950";
  if (value.includes("warning") || value.includes("error")) return "from-amber-300 to-orange-500 text-amber-950";
  return "from-emerald-300 to-teal-500 text-emerald-950";
}

function formatLabel(value = "") {
  return String(value || "unknown").replaceAll("_", " ");
}

function App() {
  const [activeTab, setActiveTab] = useState("problems");
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [feedStatus, setFeedStatus] = useState("Live");
  const [notice, setNotice] = useState(null);
  const [data, setData] = useState({ problems: [], incidents: [], runbook: {}, mttr: [] });
  const shouldReduceMotion = useReducedMotion();

  const refresh = async () => {
    const [problems, incidents, runbook, mttr] = await Promise.all([
      api.problems(),
      api.incidents(),
      api.runbook(),
      api.mttr(),
    ]);
    setData({
      problems: problems.problems ?? [],
      incidents: incidents.incidents ?? [],
      runbook: runbook.runbook ?? {},
      mttr: mttr.points ?? [],
    });
    setLoading(false);
  };

  useEffect(() => {
    refresh();
    const source = new EventSource("/api/events");
    source.onmessage = (event) => {
      setFeedStatus("Live");
      setData((current) => ({ ...current, problems: JSON.parse(event.data).problems ?? [] }));
    };
    source.onerror = () => setFeedStatus("Reconnecting");
    return () => source.close();
  }, []);

  const stats = useMemo(() => {
    const latest = data.mttr.at(-1)?.minutes ?? data.incidents[0]?.mttr_minutes ?? 0;
    return [
      { label: "Open problems", value: data.problems.length, icon: BellRing, accent: "text-rose-300" },
      { label: "Incidents logged", value: data.incidents.length, icon: ShieldCheck, accent: "text-sky-300" },
      { label: "Learned patterns", value: Object.keys(data.runbook).length, icon: GitBranch, accent: "text-emerald-300" },
      { label: "Latest MTTR", value: `${latest}m`, icon: Gauge, accent: "text-violet-300" },
    ];
  }, [data]);

  const runPoll = async () => {
    setPolling(true);
    try {
      const response = await api.poll();
      if (!response.ok) throw new Error(`Poll failed with ${response.status}`);
      const payload = await response.json();
      await refresh();
      setNotice({
        tone: "success",
        title: payload.new_problems > 0 ? "Autonomous response completed" : "No new incidents",
        message:
          payload.new_problems > 0
            ? `OpsPilot handled ${payload.new_problems} Dynatrace problem and updated the learned runbook.`
            : "The demo problem was already processed locally. Clear .opspilot/processed_ids.json to replay it.",
      });
    } catch (error) {
      console.error(error);
      setNotice({
        tone: "error",
        title: "Poll failed",
        message: "The local agent route returned an error. Check the terminal running Uvicorn for details.",
      });
    } finally {
      setPolling(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#070a12] text-white antialiased">
      <AmbientBackground reduce={shouldReduceMotion} />
      <GlassNav activeTab={activeTab} setActiveTab={setActiveTab} onPoll={runPoll} polling={polling} />
      <Toast notice={notice} onClose={() => setNotice(null)} />

      <main className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 pb-12 pt-28 sm:px-6 lg:px-8">
        <Hero onPoll={runPoll} polling={polling} feedStatus={feedStatus} />

        <section aria-label="OpsPilot summary metrics" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat, index) => (
            <MetricCard key={stat.label} stat={stat} index={index} loading={loading} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
          <GlassPanel className="min-h-[520px]">
            <AnimatePresence mode="wait">
              {activeTab === "problems" && <LiveProblems key="problems" loading={loading} problems={data.problems} />}
              {activeTab === "history" && <IncidentHistory key="history" loading={loading} incidents={data.incidents} />}
              {activeTab === "mttr" && <MttrTrends key="mttr" loading={loading} points={data.mttr} />}
              {activeTab === "runbook" && <Runbook key="runbook" loading={loading} runbook={data.runbook} />}
            </AnimatePresence>
          </GlassPanel>

          <SideRail incidents={data.incidents} runbook={data.runbook} loading={loading} />
        </section>
      </main>
    </div>
  );
}

function AmbientBackground({ reduce }) {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.26),transparent_34%),radial-gradient(circle_at_75%_15%,rgba(168,85,247,0.22),transparent_28%),radial-gradient(circle_at_70%_75%,rgba(20,184,166,0.18),transparent_30%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.08),transparent_20%,rgba(255,255,255,0.04)_45%,transparent_70%)]" />
      <div className={reduce ? "hidden" : "absolute left-1/2 top-20 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl animate-float"} />
      <div className="absolute inset-0 backdrop-blur-[1px]" />
    </div>
  );
}

function GlassNav({ activeTab, setActiveTab, onPoll, polling }) {
  return (
    <motion.header
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed inset-x-4 top-4 z-30 mx-auto max-w-6xl rounded-2xl border border-white/15 bg-white/10 px-3 py-3 shadow-glass backdrop-blur-2xl"
    >
      <nav className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between" aria-label="Primary dashboard navigation">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 ring-1 ring-white/20">
            <Bot className="h-5 w-5 text-cyan-200" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-wide text-white">OpsPilot</p>
            <p className="text-xs text-white/55">Autonomous incident response</p>
          </div>
        </div>

        <div className="flex max-w-full flex-wrap items-center gap-2 rounded-2xl bg-black/15 p-1 ring-1 ring-white/10">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className="relative rounded-2xl px-4 py-2 text-sm font-medium text-white/70 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
              aria-pressed={activeTab === id}
            >
              {activeTab === id && (
                <motion.span layoutId="active-pill" className="absolute inset-0 rounded-2xl bg-white/15 shadow-glow ring-1 ring-white/20" />
              )}
              <span className="relative flex items-center gap-2">
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </span>
            </button>
          ))}
        </div>

        <TactileButton onClick={onPoll} disabled={polling}>
          {polling ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
          Run poll
        </TactileButton>
      </nav>
    </motion.header>
  );
}

function Toast({ notice, onClose }) {
  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(onClose, 5200);
    return () => window.clearTimeout(timer);
  }, [notice, onClose]);

  return (
    <AnimatePresence>
      {notice && (
        <motion.div
          initial={{ opacity: 0, y: -18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -18, scale: 0.98 }}
          className="fixed right-4 top-24 z-40 w-[min(92vw,420px)] rounded-2xl border border-white/15 bg-slate-950/70 p-4 shadow-glass backdrop-blur-2xl"
          role="status"
          aria-live="polite"
        >
          <div className="flex gap-3">
            <div
              className={`mt-1 h-2.5 w-2.5 rounded-full ${
                notice.tone === "error" ? "bg-rose-300 shadow-[0_0_18px_rgba(253,164,175,0.9)]" : "bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.9)]"
              }`}
            />
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-white">{notice.title}</p>
              <p className="mt-1 text-sm leading-5 text-white/62">{notice.message}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-8 w-8 place-items-center rounded-xl text-white/60 transition hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Hero({ onPoll, polling, feedStatus }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7 }}
      className="relative overflow-hidden rounded-3xl border border-white/15 bg-white/[0.08] p-6 shadow-glass backdrop-blur-2xl sm:p-8 lg:p-10"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/60 to-transparent" />
      <div className="grid gap-8 lg:grid-cols-[1fr_360px] lg:items-center">
        <div>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-sm text-cyan-100">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Gemini + Agent Builder + Dynatrace MCP
          </div>
          <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
            Incident response that feels instant, calm, and self-improving.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-white/68 sm:text-lg">
            OpsPilot detects production problems, gathers Dynatrace context, diagnoses root cause, executes remediation, and evolves a learned runbook after every incident.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <TactileButton onClick={onPoll} disabled={polling} large>
              {polling ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Zap className="h-5 w-5" aria-hidden="true" />}
              Trigger autonomous response
            </TactileButton>
            <a
              href="#dashboard"
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-5 text-sm font-semibold text-white/85 transition duration-300 hover:-translate-y-0.5 hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
            >
              View dashboard <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </a>
          </div>
        </div>
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="rounded-3xl border border-white/15 bg-black/20 p-4 shadow-glow backdrop-blur-xl"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-white/60">Agent status</span>
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-400/15 px-3 py-1 text-sm text-emerald-200">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.9)]" />
              {feedStatus}
            </span>
          </div>
          <div className="mt-5 space-y-3">
            {["Detect", "Diagnose", "Remediate", "Learn"].map((item, index) => (
              <div key={item} className="flex items-center gap-3 rounded-2xl bg-white/8 p-3 ring-1 ring-white/10">
                <CheckCircle2 className="h-5 w-5 text-cyan-200" aria-hidden="true" />
                <span className="font-medium text-white/85">{item}</span>
                <span className="ml-auto text-xs text-white/40">0{index + 1}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.section>
  );
}

function TactileButton({ children, large = false, ...props }) {
  return (
    <motion.button
      type="button"
      whileHover={{ y: -2, scale: 1.01 }}
      whileTap={{ y: 1, scale: 0.98 }}
      className={`${large ? "min-h-12 px-5" : "min-h-10 px-4"} inline-flex items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-slate-950 shadow-[0_12px_40px_rgba(255,255,255,0.18)] transition disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200`}
      {...props}
    >
      {children}
    </motion.button>
  );
}

function MetricCard({ stat, index, loading }) {
  const Icon = stat.icon;
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      whileHover={{ y: -5 }}
      className="group rounded-2xl border border-white/15 bg-white/[0.08] p-5 shadow-glass backdrop-blur-xl transition"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-white/55">{stat.label}</span>
        <Icon className={`h-5 w-5 ${stat.accent}`} aria-hidden="true" />
      </div>
      {loading ? <Skeleton className="mt-5 h-9 w-24" /> : <p className="mt-4 text-4xl font-semibold tracking-tight">{stat.value}</p>}
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: loading ? "35%" : `${Math.min(92, 44 + index * 14)}%` }}
          className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-400"
        />
      </div>
    </motion.article>
  );
}

function GlassPanel({ children, className = "" }) {
  return (
    <section id="dashboard" className={`rounded-3xl border border-white/15 bg-white/[0.075] p-4 shadow-glass backdrop-blur-2xl sm:p-6 ${className}`}>
      {children}
    </section>
  );
}

function Page({ title, eyebrow, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: -8, filter: "blur(8px)" }}
      transition={{ duration: 0.28 }}
    >
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.22em] text-cyan-200/80">{eyebrow}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h2>
        </div>
      </div>
      {children}
    </motion.div>
  );
}

function LiveProblems({ problems, loading }) {
  return (
    <Page title="Live problem feed" eyebrow="Dynatrace MCP">
      <div className="grid gap-4">
        {loading ? (
          <SkeletonStack />
        ) : (
          problems.map((problem, index) => (
            <motion.article
              key={problem.problemId}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.06 }}
              whileHover={{ scale: 1.01, y: -3 }}
              className="rounded-2xl border border-white/12 bg-black/18 p-5 transition hover:bg-white/[0.09]"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white">{problem.title}</h3>
                  <p className="mt-2 text-sm text-white/55">{problem.problemId} · {(problem.entityNames ?? []).join(", ")}</p>
                </div>
                <span className={`inline-flex w-fit rounded-full bg-gradient-to-r px-3 py-1 text-xs font-bold ${severityTone(problem.severityLevel)}`}>
                  {problem.severityLevel}
                </span>
              </div>
              {problem.problemUrl && (
                <a className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-cyan-200 transition hover:text-white" href={problem.problemUrl} target="_blank" rel="noreferrer">
                  Open in Dynatrace <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                </a>
              )}
            </motion.article>
          ))
        )}
      </div>
    </Page>
  );
}

function IncidentHistory({ incidents, loading }) {
  return (
    <Page title="Incident history" eyebrow="Audit trail">
      {loading ? (
        <SkeletonStack />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/15">
          <div className="grid min-w-[760px] grid-cols-[1.5fr_0.8fr_1fr_1fr_0.6fr] border-b border-white/10 px-5 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
            <span>Incident</span><span>Severity</span><span>Root cause</span><span>Action</span><span>MTTR</span>
          </div>
          <div className="overflow-x-auto">
            {incidents.map((incident) => (
              <div key={incident.problem_id} className="grid min-w-[760px] grid-cols-[1.5fr_0.8fr_1fr_1fr_0.6fr] items-center border-b border-white/8 px-5 py-4 text-sm last:border-b-0 hover:bg-white/[0.05]">
                <div>
                  <p className="font-medium text-white">{incident.title}</p>
                  <p className="mt-1 text-xs text-white/45">{incident.problem_id}</p>
                </div>
                <span className={`w-fit rounded-full bg-gradient-to-r px-3 py-1 text-xs font-bold ${severityTone(incident.severity)}`}>{incident.severity}</span>
                <span className="capitalize text-white/75">{formatLabel(incident.root_cause)}</span>
                <span className="capitalize text-white/75">{formatLabel(incident.action_taken)}</span>
                <span className="font-semibold text-cyan-100">{incident.mttr_minutes}m</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Page>
  );
}

function MttrTrends({ points, loading }) {
  const chartPoints = points.length ? points : [{ label: "demo", minutes: 12 }];
  const max = Math.max(60, ...chartPoints.map((point) => point.minutes));
  const coords = chartPoints.map((point, index) => {
    const x = 40 + (index * 880) / Math.max(chartPoints.length - 1, 1);
    const y = 250 - (point.minutes / max) * 200;
    return `${x},${y}`;
  });

  return (
    <Page title="MTTR trendline" eyebrow="Self-learning signal">
      {loading ? (
        <Skeleton className="h-80 w-full" />
      ) : (
        <div className="rounded-2xl border border-white/10 bg-black/15 p-5">
          <svg viewBox="0 0 960 300" className="h-80 w-full" role="img" aria-label="Mean time to resolve trend chart">
            {[0, 1, 2, 3, 4].map((line) => (
              <line key={line} x1="40" x2="920" y1={50 + line * 50} y2={50 + line * 50} stroke="rgba(255,255,255,0.1)" />
            ))}
            <motion.polyline
              points={coords.join(" ")}
              fill="none"
              stroke="url(#mttrGradient)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.1, ease: "easeOut" }}
            />
            <defs>
              <linearGradient id="mttrGradient" x1="0" x2="1">
                <stop offset="0%" stopColor="#67e8f9" />
                <stop offset="50%" stopColor="#60a5fa" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
            </defs>
            {coords.map((coord, index) => {
              const [x, y] = coord.split(",");
              return <circle key={coord} cx={x} cy={y} r={index === coords.length - 1 ? 8 : 6} fill="#e0f2fe" />;
            })}
          </svg>
          <p className="text-sm text-white/55">A decreasing line is the demo’s wow moment: learned remediations reducing mean time to resolve.</p>
        </div>
      )}
    </Page>
  );
}

function Runbook({ runbook, loading }) {
  const entries = Object.entries(runbook);
  return (
    <Page title="Learned runbook" eyebrow="Agent memory">
      <div className="grid gap-4 md:grid-cols-2">
        {loading ? (
          <SkeletonStack />
        ) : (
          entries.map(([cause, entry]) => (
            <motion.article key={cause} whileHover={{ y: -4 }} className="rounded-2xl border border-white/10 bg-black/18 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold capitalize text-white">{formatLabel(cause)}</h3>
                <span className="rounded-full bg-emerald-300/15 px-3 py-1 text-xs font-semibold text-emerald-100">{entry.success_rate}% success</span>
              </div>
              <p className="text-sm leading-6 text-white/65">{entry.summary}</p>
              <p className="mt-4 text-sm text-cyan-100">{entry.avg_mttr_minutes}m avg MTTR · {entry.incident_count} incidents</p>
            </motion.article>
          ))
        )}
      </div>
    </Page>
  );
}

function SideRail({ incidents, runbook, loading }) {
  const latest = incidents[0];
  return (
    <aside className="grid gap-6">
      <GlassPanel>
        <p className="text-sm font-medium uppercase tracking-[0.22em] text-cyan-200/80">Latest diagnosis</p>
        {loading ? (
          <SkeletonStack />
        ) : (
          <div className="mt-5">
            <h3 className="text-xl font-semibold">{latest?.title ?? "Waiting for incident"}</h3>
            <p className="mt-3 text-sm leading-6 text-white/60">
              {latest?.diagnosis?.root_cause_explanation ?? "Run a poll to let OpsPilot diagnose the newest Dynatrace problem."}
            </p>
            <div className="mt-5 rounded-2xl bg-white/8 p-4 ring-1 ring-white/10">
              <p className="text-xs uppercase tracking-[0.18em] text-white/40">Recommended action</p>
              <p className="mt-2 text-lg font-semibold capitalize text-cyan-100">{formatLabel(latest?.action_taken ?? "publish_alert")}</p>
            </div>
          </div>
        )}
      </GlassPanel>

      <GlassPanel>
        <p className="text-sm font-medium uppercase tracking-[0.22em] text-cyan-200/80">System posture</p>
        <div className="mt-5 space-y-3">
          {["Dynatrace MCP active", "Gemini diagnosis ready", "Agent Builder grounded", "Runbook learning"].map((item) => (
            <div key={item} className="flex items-center gap-3 rounded-2xl bg-white/8 px-4 py-3 text-sm text-white/72 ring-1 ring-white/10">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.9)]" />
              {item}
            </div>
          ))}
        </div>
      </GlassPanel>
    </aside>
  );
}

function Skeleton({ className }) {
  return <div className={`relative overflow-hidden rounded-2xl bg-white/10 ${className}`}><div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-white/18 to-transparent" /></div>;
}

function SkeletonStack() {
  return (
    <div className="grid gap-4">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
