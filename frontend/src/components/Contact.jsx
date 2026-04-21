import { motion } from "framer-motion";
import { Github, Instagram, Mail, ArrowUpRight } from "lucide-react";

const LINKS = [
  {
    icon: Github,
    label: "GitHub",
    handle: "@Aaron-Samuel05",
    href: "https://github.com/Aaron-Samuel05",
    testid: "contact-github",
  },
  {
    icon: Instagram,
    label: "Instagram",
    handle: "@aaron_samuel05",
    href: "https://www.instagram.com/aaron_samuel05/",
    testid: "contact-instagram",
  },
  {
    icon: Mail,
    label: "Email",
    handle: "aaronsamuel0205@gmail.com",
    href: "mailto:aaronsamuel0205@gmail.com",
    testid: "contact-email",
  },
];

export default function Contact() {
  return (
    <section
      id="contact"
      className="relative py-24 md:py-32 border-t border-zinc-900"
      data-testid="contact-section"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="max-w-2xl mb-14 md:mb-20">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">
            Contact
          </div>
          <h2 className="font-heading text-4xl md:text-5xl font-semibold tracking-tight text-white leading-tight">
            Say hi.
            <br />
            <span className="text-zinc-500">Let's build something good.</span>
          </h2>
          <p className="mt-5 text-base md:text-lg text-zinc-400 leading-relaxed">
            Got feedback, a partnership idea, or just want to talk training?
            I'm most responsive on GitHub and Instagram.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          {LINKS.map((l, i) => {
            const Icon = l.icon;
            return (
              <motion.a
                key={l.label}
                href={l.href}
                target={l.href.startsWith("mailto:") ? "_self" : "_blank"}
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="group bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-6 md:p-7 flex items-center justify-between hover:border-[#39FF14]/50 hover:-translate-y-0.5 transition-all duration-500"
                data-testid={l.testid}
              >
                <div className="flex items-center gap-4 min-w-0">
                  <span className="w-11 h-11 rounded-xl bg-black border border-zinc-800 flex items-center justify-center text-[#39FF14] shrink-0 group-hover:border-[#39FF14]/50 transition-colors">
                    <Icon size={18} strokeWidth={2} />
                  </span>
                  <div className="min-w-0">
                    <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                      {l.label}
                    </div>
                    <div className="text-white font-medium truncate">{l.handle}</div>
                  </div>
                </div>
                <ArrowUpRight
                  size={18}
                  className="text-zinc-500 group-hover:text-[#39FF14] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all"
                />
              </motion.a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
