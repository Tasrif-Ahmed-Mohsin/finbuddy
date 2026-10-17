import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api, type Role } from './api';
import { defaultApiBase } from './config';
import { STRINGS, type Lang, type StringKey } from './i18n';
import { getPref, setPref } from './prefs';

type Session = {
  role: Role;
  setRole: (r: Role) => void;
  lang: Lang;
  setLang: (l: Lang) => void;
  apiBase: string;
  setApiBase: (u: string) => void;
  t: (key: StringKey) => string;
  call: <T>(path: string, init?: RequestInit) => Promise<T>;
  /** Saved preferences have been read (role, language, first launch). */
  ready: boolean;
  /** The first-launch welcome was completed (or skipped). */
  onboarded: boolean;
  setOnboarded: (v: boolean) => void;
};

const SessionContext = createContext<Session | null>(null);
const ROLES: Role[] = ['parent', 'student'];
const LANGS: Lang[] = ['en', 'bn', 'zh'];

export function SessionProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>('parent');
  const [lang, setLangState] = useState<Lang>('en');
  const [apiBase, setApiBase] = useState<string>(defaultApiBase());
  const [ready, setReady] = useState(false);
  const [onboarded, setOnboardedState] = useState(true);

  useEffect(() => {
    let live = true;
    Promise.all([getPref('role'), getPref('lang'), getPref('onboarded')]).then(([r, l, o]) => {
      if (!live) return;
      if (r && ROLES.includes(r as Role)) setRoleState(r as Role);
      if (l && LANGS.includes(l as Lang)) setLangState(l as Lang);
      setOnboardedState(o === '1');
      setReady(true);
    });
    return () => {
      live = false;
    };
  }, []);

  const setRole = useCallback((r: Role) => {
    setRoleState(r);
    void setPref('role', r);
  }, []);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    void setPref('lang', l);
  }, []);
  const setOnboarded = useCallback((v: boolean) => {
    setOnboardedState(v);
    void setPref('onboarded', v ? '1' : '0');
  }, []);

  const t = useCallback((key: StringKey) => STRINGS[lang][key] ?? STRINGS.en[key], [lang]);
  const call = useCallback(<T,>(path: string, init?: RequestInit) => api<T>(apiBase, role, path, init), [apiBase, role]);

  const value = useMemo(
    () => ({ role, setRole, lang, setLang, apiBase, setApiBase, t, call, ready, onboarded, setOnboarded }),
    [role, setRole, lang, setLang, apiBase, t, call, ready, onboarded, setOnboarded],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error('useSession must be used inside SessionProvider');
  return s;
}
