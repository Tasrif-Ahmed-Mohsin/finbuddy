import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { api, post, type Role } from './api';
import { defaultApiBase } from './config';
import { STRINGS, type Lang, type StringKey } from './i18n';
import { getPref, setPref } from './prefs';

/** Each person's answer about the AI: true = yes, false = no, null = not asked yet (then the rules answer). */
export type AiChoices = Record<Role, boolean | null>;

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
  aiChoices: AiChoices;
  /** Record these people's answer about the AI: sent to the server and saved on this phone. */
  setAiChoice: (roles: Role[], allowed: boolean) => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);
const ROLES: Role[] = ['parent', 'student'];
const LANGS: Lang[] = ['en', 'bn', 'zh'];
const asChoice = (v: string | null) => (v === '1' ? true : v === '0' ? false : null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>('parent');
  const [lang, setLangState] = useState<Lang>('en');
  const [apiBase, setApiBase] = useState<string>(defaultApiBase());
  const [ready, setReady] = useState(false);
  const [onboarded, setOnboardedState] = useState(true);
  const [aiChoices, setAiChoices] = useState<AiChoices>({ parent: null, student: null });
  const choicesRef = useRef(aiChoices);

  useEffect(() => {
    let live = true;
    Promise.all([getPref('role'), getPref('lang'), getPref('onboarded'), getPref('ai.parent'), getPref('ai.student')]).then(
      ([r, l, o, ap, as]) => {
        if (!live) return;
        if (r && ROLES.includes(r as Role)) setRoleState(r as Role);
        if (l && LANGS.includes(l as Lang)) setLangState(l as Lang);
        setOnboardedState(o === '1');
        const choices = { parent: asChoice(ap), student: asChoice(as) };
        choicesRef.current = choices;
        setAiChoices(choices);
        setReady(true);
      },
    );
    return () => {
      live = false;
    };
  }, []);

  // The server keeps the sandbox in memory: after it restarts, tell it again what each person chose on this phone.
  useEffect(() => {
    if (!ready) return;
    for (const r of ROLES) {
      const allowed = choicesRef.current[r];
      if (allowed !== null) api(apiBase, r, '/privacy/ai', post({ allowed })).catch(() => undefined);
    }
  }, [ready, apiBase]);

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
  const setAiChoice = useCallback(
    async (roles: Role[], allowed: boolean) => {
      await Promise.all(roles.map((r) => api(apiBase, r, '/privacy/ai', post({ allowed }))));
      const next = { ...choicesRef.current };
      for (const r of roles) {
        next[r] = allowed;
        void setPref(`ai.${r}`, allowed ? '1' : '0');
      }
      choicesRef.current = next;
      setAiChoices(next);
    },
    [apiBase],
  );

  const t = useCallback((key: StringKey) => STRINGS[lang][key] ?? STRINGS.en[key], [lang]);
  const call = useCallback(<T,>(path: string, init?: RequestInit) => api<T>(apiBase, role, path, init), [apiBase, role]);

  const value = useMemo(
    () => ({ role, setRole, lang, setLang, apiBase, setApiBase, t, call, ready, onboarded, setOnboarded, aiChoices, setAiChoice }),
    [role, setRole, lang, setLang, apiBase, t, call, ready, onboarded, setOnboarded, aiChoices, setAiChoice],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error('useSession must be used inside SessionProvider');
  return s;
}
