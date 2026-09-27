import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { JobResult, ScenarioConfig } from '../api/types';

export type Screen = 'setup' | 'live-run' | 'results' | 'green-impact';

interface AppState {
  screen: Screen;
  scenario: ScenarioConfig | null;
  jobId: string | null;
  convergenceHistory: number[];
  streamError: string | null;
  streamComplete: boolean;
  result: JobResult | null;
  howItWorksOpen: boolean;
}

interface AppActions {
  goTo: (screen: Screen) => void;
  startJob: (scenario: ScenarioConfig, jobId: string) => void;
  appendProgress: (gbest: number) => void;
  markStreamComplete: () => void;
  markStreamError: (message: string) => void;
  setResult: (result: JobResult) => void;
  setHowItWorksOpen: (open: boolean) => void;
}

const StateContext = createContext<AppState | null>(null);
const ActionsContext = createContext<AppActions | null>(null);

const INITIAL_STATE: AppState = {
  screen: 'setup',
  scenario: null,
  jobId: null,
  convergenceHistory: [],
  streamError: null,
  streamComplete: false,
  result: null,
  howItWorksOpen: false,
};

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  const actions = useMemo<AppActions>(
    () => ({
      goTo: (screen) => setState((s) => ({ ...s, screen })),
      startJob: (scenario, jobId) =>
        setState((s) => ({
          ...s,
          scenario,
          jobId,
          convergenceHistory: [],
          streamError: null,
          streamComplete: false,
          result: null,
          screen: 'live-run',
        })),
      appendProgress: (gbest) =>
        setState((s) => ({ ...s, convergenceHistory: [...s.convergenceHistory, gbest] })),
      markStreamComplete: () => setState((s) => ({ ...s, streamComplete: true })),
      markStreamError: (message) => setState((s) => ({ ...s, streamError: message })),
      setResult: (result) => setState((s) => ({ ...s, result })),
      setHowItWorksOpen: (open) => setState((s) => ({ ...s, howItWorksOpen: open })),
    }),
    []
  );

  return (
    <StateContext.Provider value={state}>
      <ActionsContext.Provider value={actions}>{children}</ActionsContext.Provider>
    </StateContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(StateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}

export function useAppActions(): AppActions {
  const ctx = useContext(ActionsContext);
  if (!ctx) throw new Error('useAppActions must be used within AppStateProvider');
  return ctx;
}
