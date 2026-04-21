import { useEffect, useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, LogOut, Plus, Trash2, Dumbbell, Flame, BarChart3,
  Calendar, Loader2, Target, Home, ClipboardList, X,
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiErrorDetail } from "@/lib/api";

function StatCard({ icon: Icon, label, value, unit, testid }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-5 flex items-center gap-4"
      data-testid={testid}
    >
      <span className="w-11 h-11 rounded-xl bg-black border border-[#39FF14]/30 flex items-center justify-center text-[#39FF14]">
        <Icon size={18} />
      </span>
      <div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">{label}</div>
        <div className="font-heading text-2xl font-semibold text-white tracking-tight">
          {value}
          {unit && <span className="text-zinc-500 text-base font-normal ml-1">{unit}</span>}
        </div>
      </div>
    </motion.div>
  );
}

function WeeklyChart({ data }) {
  return (
    <div className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-5" data-testid="weekly-chart">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Weekly volume</div>
        <div className="text-[11px] text-zinc-600">Last 8 weeks</div>
      </div>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f22" vertical={false} />
            <XAxis
              dataKey="week"
              tick={{ fill: "#52525b", fontSize: 10 }}
              tickFormatter={(v) => {
                const d = new Date(v);
                return `${d.getMonth() + 1}/${d.getDate()}`;
              }}
              axisLine={{ stroke: "#27272a" }}
              tickLine={false}
            />
            <YAxis tick={{ fill: "#52525b", fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#0a0a0a", border: "1px solid #27272a", borderRadius: 12, fontSize: 12 }}
              labelStyle={{ color: "#a1a1aa" }}
              formatter={(v) => [v, "volume"]}
            />
            <Bar dataKey="volume" fill="#39FF14" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function LogWorkoutModal({ open, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [exercises, setExercises] = useState([
    { name: "", sets: [{ reps: 8, weight: 0 }] },
  ]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      setName("");
      setNotes("");
      setExercises([{ name: "", sets: [{ reps: 8, weight: 0 }] }]);
      setDate(new Date().toISOString().slice(0, 10));
    }
  }, [open]);

  if (!open) return null;

  const addExercise = () =>
    setExercises((xs) => [...xs, { name: "", sets: [{ reps: 8, weight: 0 }] }]);

  const removeExercise = (idx) =>
    setExercises((xs) => xs.filter((_, i) => i !== idx));

  const updateExName = (idx, v) =>
    setExercises((xs) => xs.map((x, i) => (i === idx ? { ...x, name: v } : x)));

  const addSet = (exIdx) =>
    setExercises((xs) =>
      xs.map((x, i) =>
        i === exIdx ? { ...x, sets: [...x.sets, { reps: 8, weight: 0 }] } : x
      )
    );

  const removeSet = (exIdx, setIdx) =>
    setExercises((xs) =>
      xs.map((x, i) =>
        i === exIdx ? { ...x, sets: x.sets.filter((_, si) => si !== setIdx) } : x
      )
    );

  const updateSet = (exIdx, setIdx, field, raw) => {
    const v = Number(raw);
    if (Number.isNaN(v) || v < 0) return;
    setExercises((xs) =>
      xs.map((x, i) =>
        i === exIdx
          ? {
              ...x,
              sets: x.sets.map((s, si) =>
                si === setIdx ? { ...s, [field]: v } : s
              ),
            }
          : x
      )
    );
  };

  const save = async () => {
    if (!name.trim()) {
      toast.error("Give this workout a name.");
      return;
    }
    const cleaned = exercises
      .map((x) => ({
        name: x.name.trim(),
        sets: x.sets.filter((s) => s.reps > 0 || s.weight > 0),
      }))
      .filter((x) => x.name && x.sets.length > 0);
    if (cleaned.length === 0) {
      toast.error("Add at least one exercise with a set.");
      return;
    }

    setSaving(true);
    try {
      const { data } = await api.post("/workouts", {
        name: name.trim(),
        date,
        notes: notes.trim(),
        exercises: cleaned,
      });
      toast.success("Workout logged.");
      onCreated?.(data);
      onClose();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-start md:items-center justify-center p-4 overflow-y-auto"
      onClick={onClose}
      data-testid="log-workout-modal"
    >
      <div
        className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl w-full max-w-2xl p-6 md:p-8 my-8 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-500 hover:text-white"
          aria-label="Close"
          data-testid="log-workout-close"
        >
          <X size={18} />
        </button>

        <div className="mb-5">
          <div className="text-xs uppercase tracking-[0.2em] text-[#39FF14] font-medium mb-2">
            New workout
          </div>
          <h2 className="font-heading text-2xl md:text-3xl font-semibold text-white tracking-tight">
            Log your session
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workout name (e.g. Push Day)"
            className="md:col-span-2 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
            data-testid="workout-name-input"
          />
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
            data-testid="workout-date-input"
          />
        </div>

        <div className="space-y-4 mb-5">
          {exercises.map((ex, ei) => (
            <div key={ei} className="bg-black/60 border border-zinc-800 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <input
                  value={ex.name}
                  onChange={(e) => updateExName(ei, e.target.value)}
                  placeholder={`Exercise ${ei + 1} (e.g. Bench Press)`}
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                  data-testid={`exercise-name-${ei}`}
                />
                {exercises.length > 1 && (
                  <button
                    onClick={() => removeExercise(ei)}
                    className="text-zinc-500 hover:text-red-400 transition-colors"
                    aria-label="Remove exercise"
                    data-testid={`remove-exercise-${ei}`}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              <div className="space-y-2">
                {ex.sets.map((s, si) => (
                  <div key={si} className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-2 text-[11px] text-zinc-500 uppercase tracking-wider">
                      Set {si + 1}
                    </div>
                    <div className="col-span-4">
                      <label className="block text-[10px] text-zinc-600 uppercase tracking-wider mb-1">Reps</label>
                      <input
                        type="number"
                        min="0"
                        value={s.reps}
                        onChange={(e) => updateSet(ei, si, "reps", e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                        data-testid={`set-reps-${ei}-${si}`}
                      />
                    </div>
                    <div className="col-span-5">
                      <label className="block text-[10px] text-zinc-600 uppercase tracking-wider mb-1">Weight</label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        value={s.weight}
                        onChange={(e) => updateSet(ei, si, "weight", e.target.value)}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                        data-testid={`set-weight-${ei}-${si}`}
                      />
                    </div>
                    <div className="col-span-1 flex justify-end">
                      {ex.sets.length > 1 && (
                        <button
                          onClick={() => removeSet(ei, si)}
                          className="text-zinc-500 hover:text-red-400"
                          aria-label="Remove set"
                          data-testid={`remove-set-${ei}-${si}`}
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => addSet(ei)}
                className="mt-3 text-xs text-[#39FF14] hover:text-white transition-colors inline-flex items-center gap-1"
                data-testid={`add-set-${ei}`}
              >
                <Plus size={12} /> Add set
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={addExercise}
          className="w-full mb-5 border border-dashed border-zinc-800 rounded-xl py-3 text-sm text-zinc-400 hover:border-[#39FF14]/40 hover:text-[#39FF14] transition-colors inline-flex items-center justify-center gap-2"
          data-testid="add-exercise-btn"
        >
          <Plus size={14} /> Add exercise
        </button>

        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Notes (optional)"
          className="w-full mb-5 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
          data-testid="workout-notes-input"
        />

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2.5 text-sm text-zinc-300 hover:bg-zinc-900 rounded-full border border-zinc-800 transition-colors"
            data-testid="log-workout-cancel"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-6 py-2.5 bg-[#39FF14] text-black text-sm font-semibold rounded-full hover:bg-[#32E612] transition-all shadow-[0_0_20px_rgba(57,255,20,0.25)] disabled:opacity-60 inline-flex items-center gap-2"
            data-testid="log-workout-save"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            Save workout
          </button>
        </div>
      </div>
    </div>
  );
}

function WorkoutCard({ w, onDelete }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-5 hover:border-[#39FF14]/40 transition-colors"
      data-testid={`workout-card-${w.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500 flex items-center gap-1.5">
            <Calendar size={11} /> {w.date}
          </div>
          <h4 className="font-heading text-lg font-semibold text-white tracking-tight mt-0.5">
            {w.name}
          </h4>
        </div>
        <button
          onClick={() => onDelete(w.id)}
          className="text-zinc-500 hover:text-red-400 transition-colors"
          aria-label="Delete workout"
          data-testid={`delete-workout-${w.id}`}
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="flex gap-4 text-[11px] text-zinc-500 mb-3">
        <span className="inline-flex items-center gap-1"><Dumbbell size={11} /> {w.exercises?.length || 0} exercises</span>
        <span>·</span>
        <span>{w.total_sets || 0} sets</span>
        <span>·</span>
        <span className="text-[#39FF14]">vol {w.volume || 0}</span>
      </div>

      <ul className="space-y-1">
        {(w.exercises || []).slice(0, 4).map((ex, i) => (
          <li key={i} className="text-sm text-zinc-300 flex items-center justify-between">
            <span className="truncate">{ex.name}</span>
            <span className="text-zinc-500 text-xs">
              {(ex.sets || []).length} × {" "}
              {(ex.sets || [])
                .map((s) => `${s.reps}×${s.weight}`)
                .slice(0, 3)
                .join(", ")}
              {(ex.sets || []).length > 3 ? "…" : ""}
            </span>
          </li>
        ))}
        {(w.exercises || []).length > 4 && (
          <li className="text-xs text-zinc-600">+ {w.exercises.length - 4} more</li>
        )}
      </ul>

      {w.notes && (
        <div className="mt-3 text-xs text-zinc-500 italic border-t border-zinc-900 pt-3 line-clamp-2">
          {w.notes}
        </div>
      )}
    </motion.div>
  );
}

function PlansPanel({ plans, onCreate, onDelete }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [days, setDays] = useState([{ name: "Day 1", exercises: "" }]);

  const reset = () => {
    setName("");
    setGoal("");
    setDays([{ name: "Day 1", exercises: "" }]);
  };

  const save = async () => {
    if (!name.trim()) return toast.error("Plan needs a name.");
    const normalizedDays = days
      .map((d) => ({
        name: d.name.trim(),
        exercises: d.exercises
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }))
      .filter((d) => d.name && d.exercises.length);
    if (normalizedDays.length === 0)
      return toast.error("Add at least one day with exercises.");
    await onCreate({ name: name.trim(), goal: goal.trim(), days: normalizedDays });
    reset();
    setOpen(false);
  };

  return (
    <div className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-5" data-testid="plans-panel">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-zinc-500">Plans</div>
          <div className="font-heading text-lg font-semibold text-white tracking-tight">
            Your training programs
          </div>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="text-xs inline-flex items-center gap-1 text-[#39FF14] hover:text-white transition-colors"
          data-testid="toggle-new-plan"
        >
          <Plus size={12} /> New plan
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 mb-4">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Plan name (e.g. PPL 6-day)"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                data-testid="plan-name-input"
              />
              <input
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Goal (optional)"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                data-testid="plan-goal-input"
              />
              {days.map((d, i) => (
                <div key={i} className="grid grid-cols-5 gap-2">
                  <input
                    value={d.name}
                    onChange={(e) =>
                      setDays((ds) => ds.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))
                    }
                    className="col-span-2 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                    data-testid={`plan-day-name-${i}`}
                  />
                  <input
                    value={d.exercises}
                    onChange={(e) =>
                      setDays((ds) =>
                        ds.map((x, j) => (j === i ? { ...x, exercises: e.target.value } : x))
                      )
                    }
                    placeholder="exercises, comma separated"
                    className="col-span-3 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14]"
                    data-testid={`plan-day-exercises-${i}`}
                  />
                </div>
              ))}
              <button
                onClick={() => setDays((ds) => [...ds, { name: `Day ${ds.length + 1}`, exercises: "" }])}
                className="text-xs text-zinc-400 hover:text-[#39FF14] transition-colors inline-flex items-center gap-1"
                data-testid="plan-add-day"
              >
                <Plus size={11} /> Add day
              </button>
            </div>

            <div className="flex items-center gap-2 mb-4">
              <button
                onClick={save}
                className="px-4 py-2 bg-[#39FF14] text-black text-xs font-semibold rounded-full hover:bg-[#32E612] transition-colors"
                data-testid="plan-save"
              >
                Save plan
              </button>
              <button
                onClick={() => { reset(); setOpen(false); }}
                className="px-4 py-2 text-xs text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {plans.length === 0 ? (
        <div className="text-sm text-zinc-500 py-6 text-center border border-dashed border-zinc-800 rounded-xl">
          No plans yet. Create your first training program.
        </div>
      ) : (
        <ul className="space-y-2">
          {plans.map((p) => (
            <li
              key={p.id}
              className="bg-black/60 border border-zinc-800 rounded-xl p-3 flex items-start justify-between gap-3"
              data-testid={`plan-item-${p.id}`}
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-white truncate">{p.name}</div>
                {p.goal && <div className="text-[11px] text-zinc-500 truncate">{p.goal}</div>}
                <div className="text-[11px] text-zinc-600 mt-1">
                  {p.days.length} day{p.days.length === 1 ? "" : "s"} ·{" "}
                  {p.days.map((d) => d.name).slice(0, 3).join(", ")}
                  {p.days.length > 3 ? "…" : ""}
                </div>
              </div>
              <button
                onClick={() => onDelete(p.id)}
                className="text-zinc-500 hover:text-red-400 transition-colors"
                aria-label="Delete plan"
                data-testid={`delete-plan-${p.id}`}
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [stats, setStats] = useState(null);
  const [workouts, setWorkouts] = useState([]);
  const [plans, setPlans] = useState([]);
  const [logOpen, setLogOpen] = useState(false);

  const loadAll = async () => {
    try {
      const [statsRes, wRes, pRes] = await Promise.all([
        api.get("/workouts/stats"),
        api.get("/workouts"),
        api.get("/plans"),
      ]);
      setStats(statsRes.data);
      setWorkouts(wRes.data.workouts || []);
      setPlans(pRes.data.plans || []);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoadingInitial(false);
    }
  };

  useEffect(() => {
    if (user && typeof user === "object") loadAll();
  }, [user]);

  if (user === null) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="animate-spin text-[#39FF14]" />
      </div>
    );
  }
  if (user === false) return <Navigate to="/" replace />;

  const handleCreated = async (w) => {
    setWorkouts((ws) => [w, ...ws]);
    const { data } = await api.get("/workouts/stats");
    setStats(data);
  };

  const handleDeleteWorkout = async (id) => {
    try {
      await api.delete(`/workouts/${id}`);
      setWorkouts((ws) => ws.filter((w) => w.id !== id));
      const { data } = await api.get("/workouts/stats");
      setStats(data);
      toast.success("Workout deleted.");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    }
  };

  const handleCreatePlan = async (plan) => {
    try {
      const { data } = await api.post("/plans", plan);
      setPlans((ps) => [data, ...ps]);
      toast.success("Plan saved.");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    }
  };

  const handleDeletePlan = async (id) => {
    try {
      await api.delete(`/plans/${id}`);
      setPlans((ps) => ps.filter((p) => p.id !== id));
      toast.success("Plan removed.");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    }
  };

  const totalVolume = stats?.total_volume ?? 0;

  return (
    <main className="min-h-screen bg-black text-white" data-testid="dashboard-page">
      {/* Dashboard header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-black/70 border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-white font-heading font-semibold tracking-tight">
            <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-[#39FF14]/10 border border-[#39FF14]/40 text-[#39FF14]">
              <Activity size={16} strokeWidth={2.5} />
            </span>
            FitCheck
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-zinc-400">
            <Link to="/" className="hover:text-white transition-colors inline-flex items-center gap-1.5" data-testid="dashboard-nav-home">
              <Home size={13} /> Home
            </Link>
            <span className="text-[#39FF14] inline-flex items-center gap-1.5" data-testid="dashboard-nav-active">
              <ClipboardList size={13} /> Dashboard
            </span>
          </nav>
          <div className="flex items-center gap-2">
            <span className="hidden sm:block text-xs text-zinc-500 max-w-[180px] truncate" data-testid="user-email">
              {user.email}
            </span>
            <button
              onClick={logout}
              className="text-sm text-white px-3 py-2 rounded-full hover:bg-zinc-900 transition-colors border border-transparent hover:border-zinc-800 inline-flex items-center gap-1.5"
              data-testid="logout-btn"
            >
              <LogOut size={13} /> Log out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 md:px-10 py-10 md:py-14">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-10"
        >
          <div>
            <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-2">
              Your dashboard
            </div>
            <h1 className="font-heading text-3xl md:text-4xl font-semibold text-white tracking-tight">
              Hey, {user.email.split("@")[0]}.
            </h1>
            <p className="text-zinc-500 text-sm md:text-base mt-1">
              Log today's session, see your trend, keep the streak alive.
            </p>
          </div>
          <button
            onClick={() => setLogOpen(true)}
            className="self-start bg-[#39FF14] text-black font-semibold px-5 py-3 rounded-full hover:bg-[#32E612] transition-all shadow-[0_0_24px_rgba(57,255,20,0.25)] hover:shadow-[0_0_48px_rgba(57,255,20,0.5)] hover:-translate-y-0.5 inline-flex items-center gap-2"
            data-testid="open-log-workout"
          >
            <Plus size={16} /> Log workout
          </button>
        </motion.div>

        {loadingInitial ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="animate-spin text-[#39FF14]" />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <StatCard icon={Dumbbell} label="Workouts" value={stats?.total_workouts ?? 0} testid="stat-workouts" />
              <StatCard icon={BarChart3} label="Total volume" value={totalVolume.toLocaleString()} testid="stat-volume" />
              <StatCard icon={Target} label="Total sets" value={stats?.total_sets ?? 0} testid="stat-sets" />
              <StatCard icon={Flame} label="Streak" value={stats?.streak_days ?? 0} unit="days" testid="stat-streak" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              <div className="lg:col-span-2">
                <WeeklyChart data={stats?.weekly || []} />
              </div>
              <PlansPanel plans={plans} onCreate={handleCreatePlan} onDelete={handleDeletePlan} />
            </div>

            <div className="flex items-center justify-between mb-5">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Recent workouts</div>
                <h2 className="font-heading text-xl md:text-2xl font-semibold text-white tracking-tight">
                  Your training log
                </h2>
              </div>
            </div>

            {workouts.length === 0 ? (
              <div className="border border-dashed border-zinc-800 rounded-2xl p-12 text-center" data-testid="workouts-empty">
                <Dumbbell size={28} className="text-zinc-700 mx-auto mb-4" />
                <div className="text-white font-medium mb-1">No workouts logged yet.</div>
                <div className="text-sm text-zinc-500 mb-6">Log your first session to start seeing your trend.</div>
                <button
                  onClick={() => setLogOpen(true)}
                  className="bg-[#39FF14] text-black font-semibold px-5 py-2.5 rounded-full hover:bg-[#32E612] transition-colors inline-flex items-center gap-2"
                  data-testid="empty-log-workout"
                >
                  <Plus size={14} /> Log your first workout
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="workouts-list">
                <AnimatePresence>
                  {workouts.map((w) => (
                    <WorkoutCard key={w.id} w={w} onDelete={handleDeleteWorkout} />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </>
        )}
      </div>

      <LogWorkoutModal open={logOpen} onClose={() => setLogOpen(false)} onCreated={handleCreated} />
    </main>
  );
}
