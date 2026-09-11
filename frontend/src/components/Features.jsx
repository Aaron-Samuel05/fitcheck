import { motion } from "framer-motion";
import { Dumbbell, LineChart, ClipboardList } from "lucide-react";

const FEATURES = [
  {
    icon: Dumbbell,
    title: "Log Workouts",
    description:
      "Capture sets, reps, tempo, and RPE in seconds. Your entire training history, searchable and clean.",
    accent: "From warm-up to last set — zero friction.",
  },
  {
    icon: LineChart,
    title: "Track Progress",
    description:
      "See strength, volume, and recovery trend over weeks and months. Insights that feel inevitable, not noisy.",
    accent: "Beautiful charts that tell the truth.",
  },
  {
    icon: ClipboardList,
    title: "Custom Plans",
    description:
      "Follow adaptive programs built for your goal — strength, hypertrophy, or conditioning — and adjust on the fly.",
    accent: "Programs that move with you.",
  },
];

export default function Features() {
  return (
    <section
      id="features"
      className="relative py-24 md:py-32 border-t border-zinc-900"
      data-testid="features-section"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="max-w-2xl mb-14 md:mb-20">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">
            Features
          </div>
          <h2 className="font-heading text-4xl md:text-5xl font-semibold tracking-tight text-white leading-tight">
            Everything you need.
            <br />
            <span className="text-zinc-500">Nothing you don't.</span>
          </h2>
          <p className="mt-5 text-base md:text-lg text-zinc-400 leading-relaxed">
            A focused toolkit for people who take training seriously — without
            the bloat of traditional fitness apps.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="group relative bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-8 overflow-hidden transition-all duration-500 hover:border-[#39FF14]/50 hover:-translate-y-1"
                data-testid={`feature-card-${i}`}
              >
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                  style={{
                    background:
                      "radial-gradient(120% 80% at 0% 0%, rgba(57,255,20,0.08), transparent 60%)",
                  }}
                  aria-hidden="true"
                />
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl bg-zinc-900 flex items-center justify-center border border-zinc-800 mb-7 text-[#39FF14] group-hover:scale-110 group-hover:border-[#39FF14]/50 transition-all duration-500">
                    <Icon size={20} strokeWidth={2} />
                  </div>
                  <h3 className="font-heading text-xl md:text-2xl font-medium text-white tracking-tight mb-3">
                    {f.title}
                  </h3>
                  <p className="text-sm md:text-base text-zinc-400 leading-relaxed mb-6">
                    {f.description}
                  </p>
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-600 group-hover:text-[#39FF14] transition-colors">
                    {f.accent}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
