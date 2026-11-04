import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeContextProvider } from './theme/ThemeContext';
import { PlantContextProvider } from './context/PlantContext';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { PlantProfilePage } from './pages/PlantProfilePage';
import { DataImportPage } from './pages/DataImportPage';
import { PerformancePage } from './pages/PerformancePage';
import { InvertersPage } from './pages/InvertersPage';
import { LossesPage } from './pages/LossesPage';
import { DegradationPage } from './pages/DegradationPage';
import { IrradiationPage } from './pages/IrradiationPage';
import { AlertsPage } from './pages/AlertsPage';
import { ReportsPage } from './pages/ReportsPage';
import PlaceholderPage from './pages/PlaceholderPage';

const App: React.FC = () => {
  return (
    <ThemeContextProvider>
      <PlantContextProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/plant" element={<PlantProfilePage />} />
              <Route path="/import" element={<DataImportPage />} />
              <Route path="/performance" element={<PerformancePage />} />
              <Route path="/inverters" element={<InvertersPage />} />
              <Route path="/losses" element={<LossesPage />} />
              <Route path="/degradation" element={<DegradationPage />} />
              <Route path="/irradiation" element={<IrradiationPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route
                path="/settings"
                element={
                  <PlaceholderPage
                    title="System Settings"
                    description="Configure global KPI thresholds, import mappings, and system properties."
                  />
                }
              />
            </Routes>
          </Layout>
        </Router>
      </PlantContextProvider>
    </ThemeContextProvider>
  );
};

export default App;
