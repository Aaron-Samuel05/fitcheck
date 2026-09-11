import { Activity, Github, Instagram } from "lucide-react";

// Escape the preview iframe for external links (Instagram/GitHub X-Frame-Options
// otherwise triggers ERR_BLOCKED_BY_RESPONSE).
function openExternal(href) {
  try {
    const win = (window.top || window).open(href, "_blank", "noopener,noreferrer");
    if (!win) window.location.href = href;
  } catch {
    window.location.href = href;
  }
}

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer
      className="relative border-t border-zinc-900 py-14 md:py-16"
      data-testid="site-footer"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 flex flex-col md:flex-row md:items-center md:justify-between gap-8">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-md bg-[#39FF14]/10 border border-[#39FF14]/40 text-[#39FF14]">
            <Activity size={16} strokeWidth={2.5} />
          </span>
          <div>
            <div className="font-heading text-base font-semibold text-white tracking-tight">
              FitCheck
            </div>
            <div className="text-xs text-zinc-600">
              Train with intention. Progress with proof.
            </div>
          </div>
        </div>

        <nav className="flex flex-wrap items-center gap-5 text-sm text-zinc-500">
          <a href="#features" className="hover:text-white transition-colors" data-testid="footer-features">Features</a>
          <a href="#how" className="hover:text-white transition-colors" data-testid="footer-how">How it works</a>
          <a href="#pricing" className="hover:text-white transition-colors" data-testid="footer-pricing">Pricing</a>
          <a href="#contact" className="hover:text-white transition-colors" data-testid="footer-contact">Contact</a>
          <a
            href="https://github.com/Aaron-Samuel05"
            onClick={(e) => {
              e.preventDefault();
              openExternal("https://github.com/Aaron-Samuel05");
            }}
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-500 hover:text-[#39FF14] transition-colors cursor-pointer"
            aria-label="GitHub"
            data-testid="footer-github"
          >
            <Github size={16} />
          </a>
          <a
            href="https://www.instagram.com/aaron_samuel05/"
            onClick={(e) => {
              e.preventDefault();
              openExternal("https://www.instagram.com/aaron_samuel05/");
            }}
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-500 hover:text-[#39FF14] transition-colors cursor-pointer"
            aria-label="Instagram"
            data-testid="footer-instagram"
          >
            <Instagram size={16} />
          </a>
        </nav>

        <div className="text-xs text-zinc-600" data-testid="footer-copyright">
          © {year} FitCheck · Built by{" "}
          <a
            href="https://github.com/Aaron-Samuel05"
            onClick={(e) => {
              e.preventDefault();
              openExternal("https://github.com/Aaron-Samuel05");
            }}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[#39FF14] transition-colors cursor-pointer"
          >
            @Aaron-Samuel05
          </a>
        </div>
      </div>
    </footer>
  );
}
