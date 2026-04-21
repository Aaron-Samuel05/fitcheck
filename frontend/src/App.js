import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { AuthUIProvider } from "@/context/AuthUIContext";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import HowItWorks from "@/components/HowItWorks";
import Contact from "@/components/Contact";
import Footer from "@/components/Footer";
import AIBuddyWidget from "@/components/AIBuddyWidget";
import GoogleCallbackHandler from "@/components/GoogleCallbackHandler";
import Dashboard from "@/pages/Dashboard";
import { Toaster } from "sonner";

function Landing() {
  return (
    <main
      className="relative min-h-screen bg-black text-white overflow-x-hidden"
      data-testid="landing-page"
    >
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <Contact />
      <Footer />
      <AIBuddyWidget />
      <GoogleCallbackHandler />
    </main>
  );
}

function DashboardPage() {
  return (
    <>
      <Dashboard />
      <AIBuddyWidget />
      <GoogleCallbackHandler />
    </>
  );
}

export default function App() {
  return (
    <div className="App font-sans">
      <AuthProvider>
        <BrowserRouter>
          <AuthUIProvider>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/app" element={<DashboardPage />} />
              <Route path="*" element={<Landing />} />
            </Routes>
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
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
