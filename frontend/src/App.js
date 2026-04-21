import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { AuthUIProvider, useAuthUI } from "@/context/AuthUIContext";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import HowItWorks from "@/components/HowItWorks";
import Pricing from "@/components/Pricing";
import Contact from "@/components/Contact";
import Footer from "@/components/Footer";
import AIBuddyWidget from "@/components/AIBuddyWidget";
import PaymentReturnHandler from "@/components/PaymentReturnHandler";
import GoogleCallbackHandler from "@/components/GoogleCallbackHandler";
import { Toaster } from "sonner";

function scrollToPricing() {
  const el = document.getElementById("pricing");
  if (el) el.scrollIntoView({ behavior: "smooth" });
}

function Landing() {
  const { openAuth } = useAuthUI();
  return (
    <main
      className="relative min-h-screen bg-black text-white overflow-x-hidden"
      data-testid="landing-page"
    >
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing onRequestAuth={(m) => openAuth(m)} />
      <Contact />
      <Footer />
      <AIBuddyWidget
        onRequestAuth={(m) => openAuth(m)}
        onRequestUpgrade={() => scrollToPricing()}
      />
      <PaymentReturnHandler />
      <GoogleCallbackHandler />
    </main>
  );
}

export default function App() {
  return (
    <div className="App font-sans">
      <AuthProvider>
        <AuthUIProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="*" element={<Landing />} />
            </Routes>
          </BrowserRouter>
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              style: {
                background: "#0A0A0A",
                border: "1px solid #27272A",
                color: "#fff",
              },
            }}
          />
        </AuthUIProvider>
      </AuthProvider>
    </div>
  );
}
