import { createContext, useContext } from 'react';
import type { JobResult, ScenarioConfig, SetupDraft } from '../api/types';

export type Screen = 'setup' | 'live-run' | 'results' | 'green-impact';

export interface AppState {
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

export interface AppActions {
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

export const StateContext = createContext<AppState | null>(null);
export const ActionsContext = createContext<AppActions | null>(null);

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
