import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import Footer from "@/components/Footer";
import { Toaster } from "sonner";

function Landing() {
  return (
    <main className="relative min-h-screen bg-black text-white overflow-x-hidden" data-testid="landing-page">
      <Navbar />
      <Hero />
      <Features />
      <Footer />
    </main>
  );
}

export default function App() {
  return (
    <div className="App font-sans">
      <AuthProvider>
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
      </AuthProvider>
    </div>
  );
}
