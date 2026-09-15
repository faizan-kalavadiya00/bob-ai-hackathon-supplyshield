import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Dashboard } from './pages/Dashboard'
import { ResilienceWallet } from './pages/ResilienceWallet'
import { Disruptions } from './pages/Disruptions'
import { PlaceholderPage } from './pages/PlaceholderPage'

const PAGE_TITLES: Record<string, string> = {
  '/':            'Dashboard',
  '/shipments':   'Shipments',
  '/disruptions': 'Disruptions',
  '/resilience':  'Resilience Wallet',
  '/fleet':       'Fleet & Route Optimization',
  '/cold-chain':  'Cold Chain Monitoring',
  '/simulation':  'Disruption Simulation',
  '/recovery':    'Recovery Planning',
  '/approvals':   'Approvals',
  '/audit':       'Audit Log',
}

function Layout({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Layout title={PAGE_TITLES['/']}>
              <Dashboard />
            </Layout>
          }
        />
        <Route
          path="/shipments"
          element={
            <Layout title={PAGE_TITLES['/shipments']}>
              <PlaceholderPage
                title="Shipment Tracking"
                description="Real-time shipment tracking with disruption flags, ETA, and cold-chain status."
                icon="🚢"
                phase={2}
              />
            </Layout>
          }
        />
        <Route
          path="/disruptions"
          element={
            <Layout title={PAGE_TITLES['/disruptions']}>
              <Disruptions />
            </Layout>
          }
        />
        <Route
          path="/resilience"
          element={
            <Layout title={PAGE_TITLES['/resilience']}>
              <ResilienceWallet />
            </Layout>
          }
        />
        <Route
          path="/fleet"
          element={
            <Layout title={PAGE_TITLES['/fleet']}>
              <PlaceholderPage
                title="Fleet & Route Optimization"
                description="Vehicle grid, risk-weighted route alternatives, and fleet allocation recommendations."
                icon="🚛"
                phase={3}
              />
            </Layout>
          }
        />
        <Route
          path="/cold-chain"
          element={
            <Layout title={PAGE_TITLES['/cold-chain']}>
              <PlaceholderPage
                title="Cold Chain Monitoring"
                description="IoT sensor readings, temperature breach detection, and cargo-at-risk summary."
                icon="❄"
                phase={3}
              />
            </Layout>
          }
        />
        <Route
          path="/simulation"
          element={
            <Layout title={PAGE_TITLES['/simulation']}>
              <PlaceholderPage
                title="Disruption Simulation"
                description="Scenario-based disruption simulation with RRI impact projection and before/after comparison."
                icon="🔬"
                phase={3}
              />
            </Layout>
          }
        />
        <Route
          path="/recovery"
          element={
            <Layout title={PAGE_TITLES['/recovery']}>
              <PlaceholderPage
                title="Recovery Planning"
                description="AI-assisted recovery plan steps, RRI recovery projection, and IBM Bob narrative panel."
                icon="♻"
                phase={3}
              />
            </Layout>
          }
        />
        <Route
          path="/approvals"
          element={
            <Layout title={PAGE_TITLES['/approvals']}>
              <PlaceholderPage
                title="Human Approvals"
                description="Pending high-impact action approvals, approval history, and human-in-the-loop workflow."
                icon="✅"
                phase={2}
              />
            </Layout>
          }
        />
        <Route
          path="/audit"
          element={
            <Layout title={PAGE_TITLES['/audit']}>
              <PlaceholderPage
                title="Audit Log"
                description="Immutable, paginated audit trail of all state changes with actor, source, and before/after diff."
                icon="📋"
                phase={2}
              />
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
