import { BrowserRouter, Routes, Route } from 'react-router-dom';

import LeagueConnect from '@/features/connect_league/league-connect';
import LeagueQLLanding from '@/features/landing_page/landing-page';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LeagueQLLanding />} />
        <Route path="/connect_league" element={<LeagueConnect />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
