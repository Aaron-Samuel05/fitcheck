import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Save, Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function ProfileWidget() {
  const { user, refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: "", age: "", height_cm: "", weight_kg: "", goal: "" });

  const hydrate = (profile) => {
    const p = profile || {};
    setForm({ name: p.name || "", age: p.age ?? "", height_cm: p.height_cm ?? "", weight_kg: p.weight_kg ?? "", goal: p.goal || "" });
  };

  useEffect(() => {
    if (open) hydrate(user?.profile);
  }, [open, user]);

  const openProfile = async () => {
    setOpen(true);
    setLoading(true);
    try {
      const { data } = await api.get("/profile");
      hydrate(data.profile);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message || "Could not load profile.");
    } finally {
      setLoading(false);
    }
  };

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const save = async () => {
    const age = form.age === "" ? null : Number(form.age);
    const height = form.height_cm === "" ? null : Number(form.height_cm);
    const weight = form.weight_kg === "" ? null : Number(form.weight_kg);
    if (age != null && (!Number.isFinite(age) || age < 13 || age > 100)) return toast.error("Age must be between 13 and 100.");
    if (height != null && (!Number.isFinite(height) || height < 100 || height > 250)) return toast.error("Height must be between 100 and 250 cm.");
    if (weight != null && (!Number.isFinite(weight) || weight < 25 || weight > 300)) return toast.error("Weight must be between 25 and 300 kg.");
    setSaving(true);
    try {
      const { data } = await api.patch("/profile", { name: form.name.trim(), age, height_cm: height, weight_kg: weight, goal: form.goal.trim() });
      hydrate(data.profile);
      await refresh?.();
      setOpen(false);
      toast.success("Profile updated.");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message || "Could not save profile.");
    } finally {
      setSaving(false);
    }
  };

  if (!user || typeof user !== "object") return null;
  const displayName = user.profile?.name || user.email?.split("@")[0] || "Profile";
  return (
    <>
      <button type="button" onClick={openProfile} className="fixed left-4 md:left-6 bottom-20 z-40 inline-flex items-center gap-2 px-4 py-3 rounded-full bg-[#0A0A0A] border border-zinc-800 text-white shadow-2xl hover:border-[#39FF14]/60 hover:text-[#39FF14] transition-all" data-testid="profile-launcher" aria-label="Edit profile">
        <span className="w-6 h-6 rounded-full bg-[#39FF14]/10 border border-[#39FF14]/40 text-[#39FF14] flex items-center justify-center text-xs font-semibold">{displayName.charAt(0).toUpperCase()}</span>
        <span className="text-sm font-medium">Profile</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setOpen(false)} data-testid="profile-overlay">
            <motion.div initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.98 }} onClick={(e) => e.stopPropagation()} className="w-full max-w-lg bg-[#0A0A0A] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden" data-testid="profile-modal">
              <div className="flex items-center justify-between px-6 py-5 border-b border-zinc-900">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-[#39FF14] mb-1">Your profile</div>
                  <h2 className="font-heading text-2xl font-semibold text-white">Edit your info</h2>
                  <p className="text-xs text-zinc-500 mt-1">Used to personalize your dashboard and AI Coach.</p>
                </div>
                <button type="button" onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white" aria-label="Close profile"><X size={18} /></button>
              </div>
              {loading ? (
                <div className="py-16 flex justify-center"><Loader2 className="animate-spin text-[#39FF14]" /></div>
              ) : (
                <div className="p-6 space-y-4">
                  <div><label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-2">Email</label><div className="flex items-center gap-2 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm text-zinc-500"><Mail size={15} /><span className="truncate">{user.email}</span></div><p className="text-[11px] text-zinc-600 mt-1.5">Managed by your login provider.</p></div>
                  <div><label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-2">Name</label><input value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="What should we call you?" className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#39FF14]" data-testid="profile-name-input" /></div>
                  <div className="grid grid-cols-3 gap-3">
                    {[["age", "Age", "13–100"], ["height_cm", "Height cm", "100–250"], ["weight_kg", "Weight kg", "25–300"]].map(([key, label, placeholder]) => <div key={key}><label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-2">{label}</label><input type="number" value={form[key]} onChange={(e) => update(key, e.target.value)} placeholder={placeholder} className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#39FF14]" data-testid={`profile-${key}-input`} /></div>)}
                  </div>
                  <div><label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-2">Main goal</label><input value={form.goal} onChange={(e) => update("goal", e.target.value)} placeholder="e.g. Build muscle while losing fat" className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#39FF14]" data-testid="profile-goal-input" /></div>
                  <div className="flex justify-end gap-3 pt-2"><button type="button" onClick={() => setOpen(false)} className="px-5 py-2.5 rounded-full border border-zinc-800 text-sm text-zinc-300">Cancel</button><button type="button" onClick={save} disabled={saving} className="px-5 py-2.5 rounded-full bg-[#39FF14] text-black font-semibold text-sm inline-flex items-center gap-2 disabled:opacity-60" data-testid="profile-save">{saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save changes</button></div>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
