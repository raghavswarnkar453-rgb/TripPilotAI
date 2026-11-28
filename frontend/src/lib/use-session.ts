"use client";

import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase";

export type SessionState = { loading: boolean; email: string | null; configured: boolean };

export function useSession(): SessionState {
  const [state, setState] = useState<SessionState>({ loading: true, email: null, configured: true });

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      queueMicrotask(() => setState({ loading: false, email: null, configured: false }));
      return;
    }
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (active) setState({ loading: false, email: data.session?.user.email ?? null, configured: true });
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setState({ loading: false, email: session?.user.email ?? null, configured: true });
    });
    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  return state;
}
