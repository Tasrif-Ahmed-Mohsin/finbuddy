import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import { api, type Role } from './api';
import { defaultApiBase } from './config';
import { STRINGS, type Lang, type StringKey } from './i18n';

type Session = {
  role: Role;
  setRole: (r: Role) => void;
  lang: Lang;
  setLang: (l: Lang) => void;
  apiBase: string;
  setApiBase: (u: string) => void;
  t: (key: StringKey) => string;
  call: <T>(path: string, init?: RequestInit) => Promise<T>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>('parent');
  const [lang, setLang] = useState<Lang>('en');
  const [apiBase, setApiBase] = useState<string>(defaultApiBase());

  const t = useCallback((key: StringKey) => STRINGS[lang][key] ?? STRINGS.en[key], [lang]);
  const call = useCallback(<T,>(path: string, init?: RequestInit) => api<T>(apiBase, role, path, init), [apiBase, role]);

  const value = useMemo(
    () => ({ role, setRole, lang, setLang, apiBase, setApiBase, t, call }),
    [role, lang, apiBase, t, call],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error('useSession must be used inside SessionProvider');
  return s;
}
