import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Dashboard } from './pages/Dashboard'
import { ResilienceWallet } from './pages/ResilienceWallet'
import { Disruptions } from './pages/Disruptions'
import { Shipments } from './pages/Shipments'
import { Fleet } from './pages/Fleet'
import { ColdChain } from './pages/ColdChain'
import { Simulation } from './pages/Simulation'
import { Recovery } from './pages/Recovery'
import { Approvals } from './pages/Approvals'
import { Audit } from './pages/Audit'

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
              <Shipments />
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
              <Fleet />
            </Layout>
          }
        />
        <Route
          path="/cold-chain"
          element={
            <Layout title={PAGE_TITLES['/cold-chain']}>
              <ColdChain />
            </Layout>
          }
        />
        <Route
          path="/simulation"
          element={
            <Layout title={PAGE_TITLES['/simulation']}>
              <Simulation />
            </Layout>
          }
        />
        <Route
          path="/recovery"
          element={
            <Layout title={PAGE_TITLES['/recovery']}>
              <Recovery />
            </Layout>
          }
        />
        <Route
          path="/approvals"
          element={
            <Layout title={PAGE_TITLES['/approvals']}>
              <Approvals />
            </Layout>
          }
        />
        <Route
          path="/audit"
          element={
            <Layout title={PAGE_TITLES['/audit']}>
              <Audit />
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
