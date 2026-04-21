import { Activity } from "lucide-react";

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

        <nav className="flex flex-wrap items-center gap-6 text-sm text-zinc-500">
          <a href="#features" className="hover:text-white transition-colors" data-testid="footer-features">
            Features
          </a>
          <a href="#top" className="hover:text-white transition-colors" data-testid="footer-get-started">
            Get started
          </a>
          <a href="mailto:hello@fitcheck.app" className="hover:text-white transition-colors" data-testid="footer-contact">
            Contact
          </a>
          <a href="#" className="hover:text-white transition-colors" data-testid="footer-privacy">
            Privacy
          </a>
          <a href="#" className="hover:text-white transition-colors" data-testid="footer-terms">
            Terms
          </a>
        </nav>

        <div className="text-xs text-zinc-600" data-testid="footer-copyright">
          © {year} FitCheck. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
