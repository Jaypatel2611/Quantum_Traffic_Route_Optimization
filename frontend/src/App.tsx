import { AppStateProvider, useAppState } from './state/AppState';
import { SetupScreen } from './screens/SetupScreen';
import { LiveRunScreen } from './screens/LiveRunScreen';
import { ResultsScreen } from './screens/ResultsScreen';
import { GreenImpactScreen } from './screens/GreenImpactScreen';

function ScreenRouter() {
  const { screen } = useAppState();
  switch (screen) {
    case 'setup':
      return <SetupScreen />;
    case 'live-run':
      return <LiveRunScreen />;
    case 'results':
      return <ResultsScreen />;
    case 'green-impact':
      return <GreenImpactScreen />;
  }
}

function App() {
  return (
    <AppStateProvider>
      <ScreenRouter />
    </AppStateProvider>
  );
}

export default App;
