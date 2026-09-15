import { NavLink } from 'react-router-dom'
import { ShieldIcon } from './ui/ShieldIcon'

interface NavItem {
  to: string
  label: string
  icon: string
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',              label: 'Dashboard',         icon: '◈' },
  { to: '/shipments',     label: 'Shipments',         icon: '🚢' },
  { to: '/disruptions',   label: 'Disruptions',       icon: '⚡' },
  { to: '/resilience',    label: 'Resilience Wallet', icon: '🛡' },
  { to: '/fleet',         label: 'Fleet & Routes',    icon: '🚛' },
  { to: '/cold-chain',    label: 'Cold Chain',        icon: '❄' },
  { to: '/simulation',    label: 'Simulation',        icon: '🔬' },
  { to: '/recovery',      label: 'Recovery Plans',    icon: '♻' },
  { to: '/approvals',     label: 'Approvals',         icon: '✅' },
  { to: '/audit',         label: 'Audit Log',         icon: '📋' },
]

export function Sidebar() {
  return (
    <aside className="flex flex-col w-60 min-h-screen bg-gray-900 border-r border-gray-800 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-gray-800">
        <ShieldIcon className="w-8 h-8 text-shield-500" />
        <div>
          <p className="text-sm font-bold text-white tracking-wide">SupplyShield</p>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest">
            Resilience OS
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              [
                'flex items-center gap-3 px-3 py-2 rounded-lg mb-0.5 text-sm transition-colors',
                isActive
                  ? 'bg-shield-600/30 text-shield-300 font-medium'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200',
              ].join(' ')
            }
          >
            <span className="text-base w-5 text-center select-none" aria-hidden="true">
              {item.icon}
            </span>
            <span>{item.label}</span>
            {item.badge && (
              <span className="ml-auto text-[10px] bg-red-500 text-white rounded-full px-1.5 py-0.5 font-semibold">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-[10px] text-gray-600 text-center">
          IBM Bob AI Hackathon 2025
        </p>
      </div>
    </aside>
  )
}
