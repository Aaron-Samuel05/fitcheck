import { motion } from "framer-motion";
import { Zap, Dumbbell, LineChart } from "lucide-react";

const STEPS = [
  {
    icon: Zap,
    step: "01",
    title: "Sign up in seconds",
    desc: "Create your free FitCheck account. No card, no onboarding maze — you're in.",
  },
  {
    icon: Dumbbell,
    step: "02",
    title: "Log your training",
    desc: "Capture sets, reps, tempo, and RPE. Apple-Fitness-clean, zero friction.",
  },
  {
    icon: LineChart,
    step: "03",
    title: "See the signal",
    desc: "Volume, strength, and recovery trends emerge automatically. You stay accountable.",
  },
];

export default function HowItWorks() {
  return (
    <section
      id="how"
      className="relative py-24 md:py-32 border-t border-zinc-900"
      data-testid="how-section"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="max-w-2xl mb-14 md:mb-20">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">
            How it works
          </div>
          <h2 className="font-heading text-4xl md:text-5xl font-semibold tracking-tight text-white leading-tight">
            Three steps.
            <br />
            <span className="text-zinc-500">Zero noise.</span>
          </h2>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {/* Neon connector line */}
          <div
            className="hidden md:block absolute left-0 right-0 top-14 h-px pointer-events-none"
            style={{
              background:
                "linear-gradient(90deg, transparent 0%, rgba(57,255,20,0.25) 20%, rgba(57,255,20,0.25) 80%, transparent 100%)",
            }}
            aria-hidden="true"
          />

          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-8 hover:border-[#39FF14]/40 transition-colors"
                data-testid={`step-card-${i}`}
              >
                <div className="flex items-center justify-between mb-6">
                  <span className="w-10 h-10 rounded-full bg-black border border-[#39FF14]/40 flex items-center justify-center text-[#39FF14]">
                    <Icon size={18} strokeWidth={2} />
                  </span>
                  <span className="font-heading text-xs tracking-[0.25em] text-zinc-600">
                    {s.step}
                  </span>
                </div>
                <h3 className="font-heading text-xl md:text-2xl font-medium text-white tracking-tight mb-3">
                  {s.title}
                </h3>
                <p className="text-sm md:text-base text-zinc-400 leading-relaxed">
                  {s.desc}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
