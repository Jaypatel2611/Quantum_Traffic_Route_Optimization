import { useMemo, useState, type ReactNode } from 'react';
import { INITIAL_SETUP } from './defaultScenario';
import { ActionsContext, StateContext, type AppActions, type AppState, type Screen } from './appStateHooks';

// Re-exported so existing `from './AppState'` imports keep working.
export { useAppActions, useAppState, type Screen } from './appStateHooks';

/** Live Run is a transient step (re-entering it would replay the SSE stream
 * into an already-complete history), so Results goes back to Setup. */
const BACK_TARGET: Record<Screen, Screen> = {
  setup: 'setup',
  'live-run': 'setup',
  results: 'setup',
  'green-impact': 'results',
};

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
