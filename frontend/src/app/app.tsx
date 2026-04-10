import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Header from '@/components/header';
import LeagueConnect from '@/features/connect_league/league-connect';
import LeagueQLLanding from '@/features/landing_page/landing-page';

function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<LeagueQLLanding />} />
        <Route
          path="/connect_league"
          element={
            <div className="pt-1">
              <LeagueConnect />
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
