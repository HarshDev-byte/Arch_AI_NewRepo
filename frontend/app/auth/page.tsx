"use client";

import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";

export default function AuthPage() {
  // Skip Supabase initialization during build time
  const supabase = typeof window !== 'undefined' ? createClientComponentClient() : null;
  const router   = useRouter();
  const [checking, setChecking] = useState(true);

  // Redirect immediately if already signed in
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) router.replace("/dashboard");
      else setChecking(false);
    });
  }, [supabase, router]);

  // Listen for sign-in event
  useEffect(() => {
    if (!supabase) return;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN") router.replace("/dashboard");
    });
    return () => subscription?.unsubscribe();
  }, [supabase, router]);

  // Show loading during SSR or while checking auth
  if (!supabase || checking) {
    return (
      <div className="min-h-screen bg-[#080C14] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080C14] text-white flex flex-col items-center justify-center px-4 relative overflow-hidden">

      {/* Background blobs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-violet-600/15 blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-cyan-500/8 blur-[90px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" id="auth-logo" className="text-3xl font-extrabold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
            ArchAI
          </Link>
          <p className="mt-2 text-white/50 text-sm">
            AI-powered architectural design · Sign in to get started
          </p>
        </div>

        {/* Auth card */}
        <div
          className="p-8 rounded-2xl border border-white/8 bg-white/3 backdrop-blur-xl shadow-2xl"
          id="auth-card"
        >
          <Auth
            supabaseClient={supabase!}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand:           "#7c3aed",
                    brandAccent:     "#6d28d9",
                    brandButtonText: "#ffffff",
                    defaultButtonBackground:        "rgba(255,255,255,0.05)",
                    defaultButtonBackgroundHover:   "rgba(255,255,255,0.10)",
                    inputBackground:                "rgba(255,255,255,0.05)",
                    inputBorder:                    "rgba(255,255,255,0.10)",
                    inputBorderHover:               "rgba(139,92,246,0.50)",
                    inputBorderFocus:               "#7c3aed",
                    inputText:                      "#ffffff",
                    inputPlaceholder:               "rgba(255,255,255,0.35)",
                    messageText:                    "rgba(255,255,255,0.70)",
                    anchorTextColor:                "#a78bfa",
                    anchorTextHoverColor:           "#c4b5fd",
                    dividerBackground:              "rgba(255,255,255,0.08)",
                  },
                  space: {
                    inputPadding:  "12px 14px",
                    buttonPadding: "12px 16px",
                  },
                  borderWidths: { buttonBorderWidth: "1px", inputBorderWidth: "1px" },
                  radii:        { borderRadiusButton: "10px", inputBorderRadius: "10px" },
                  fontSizes:    { baseBodySize: "14px" },
                },
              },
              style: {
                button:    { fontWeight: "600" },
                container: { gap: "16px" },
              },
            }}
            providers={["google"]}
            redirectTo={`${typeof window !== "undefined" ? window.location.origin : (process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000")}/auth/callback`}
            view="sign_in"
            showLinks={true}
            localization={{
              variables: {
                sign_in: {
                  email_label:    "Email address",
                  password_label: "Password",
                  button_label:   "Sign in to ArchAI",
                  social_provider_text: "Continue with {{provider}}",
                  link_text:      "Don't have an account? Sign up",
                },
                sign_up: {
                  button_label: "Create ArchAI account",
                  link_text:    "Already have an account? Sign in",
                },
              },
            }}
          />
        </div>

        <p className="text-center text-xs text-white/25 mt-6">
          By signing in you agree to our&nbsp;
          <span className="text-violet-400 cursor-pointer hover:underline">Terms</span>
          &nbsp;and&nbsp;
          <span className="text-violet-400 cursor-pointer hover:underline">Privacy Policy</span>
        </p>
      </motion.div>
    </div>
  );
}
