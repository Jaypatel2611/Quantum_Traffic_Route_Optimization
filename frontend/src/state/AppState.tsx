import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { JobResult, ScenarioConfig, SetupDraft } from '../api/types';
import { INITIAL_SETUP } from './defaultScenario';

export type Screen = 'setup' | 'live-run' | 'results' | 'green-impact';

interface AppState {
  screen: Screen;
  setup: SetupDraft;
  scenario: ScenarioConfig | null;
  jobId: string | null;
  convergenceHistory: number[];
  streamError: string | null;
  streamComplete: boolean;
  result: JobResult | null;
  howItWorksOpen: boolean;
  /** Results' vehicle filter: routeKey() values, or null for every vehicle. */
  visibleRoutes: string[] | null;
}

interface AppActions {
  goTo: (screen: Screen) => void;
  /** Back one workflow step. State (setup draft, result) is never cleared by going back. */
  goBack: () => void;
  updateSetup: (patch: Partial<SetupDraft>) => void;
  startJob: (scenario: ScenarioConfig, jobId: string) => void;
  appendProgress: (gbest: number) => void;
  markStreamComplete: () => void;
  markStreamError: (message: string) => void;
  setResult: (result: JobResult) => void;
  setHowItWorksOpen: (open: boolean) => void;
  setVisibleRoutes: (visible: string[] | null) => void;
}

/** Live Run is a transient step (re-entering it would replay the SSE stream
 * into an already-complete history), so Results goes back to Setup. */
const BACK_TARGET: Record<Screen, Screen> = {
  setup: 'setup',
  'live-run': 'setup',
  results: 'setup',
  'green-impact': 'results',
};

const StateContext = createContext<AppState | null>(null);
const ActionsContext = createContext<AppActions | null>(null);

const INITIAL_STATE: AppState = {
  screen: 'setup',
  setup: INITIAL_SETUP,
  scenario: null,
  jobId: null,
  convergenceHistory: [],
  streamError: null,
  streamComplete: false,
  result: null,
  howItWorksOpen: false,
  visibleRoutes: null,
};

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(INITIAL_STATE);

  const actions = useMemo<AppActions>(
    () => ({
      goTo: (screen) => setState((s) => ({ ...s, screen })),
      goBack: () => setState((s) => ({ ...s, screen: BACK_TARGET[s.screen] })),
      updateSetup: (patch) => setState((s) => ({ ...s, setup: { ...s.setup, ...patch } })),
      startJob: (scenario, jobId) =>
        setState((s) => ({
          ...s,
          scenario,
          jobId,
          convergenceHistory: [],
          streamError: null,
          streamComplete: false,
          result: null,
          visibleRoutes: null,
          screen: 'live-run',
        })),
      appendProgress: (gbest) =>
        setState((s) => ({ ...s, convergenceHistory: [...s.convergenceHistory, gbest] })),
      markStreamComplete: () => setState((s) => ({ ...s, streamComplete: true })),
      markStreamError: (message) => setState((s) => ({ ...s, streamError: message })),
      setResult: (result) => setState((s) => ({ ...s, result })),
      setHowItWorksOpen: (open) => setState((s) => ({ ...s, howItWorksOpen: open })),
      setVisibleRoutes: (visibleRoutes) => setState((s) => ({ ...s, visibleRoutes })),
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
