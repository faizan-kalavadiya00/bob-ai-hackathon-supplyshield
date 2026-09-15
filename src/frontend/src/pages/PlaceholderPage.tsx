interface PlaceholderPageProps {
  title: string
  description: string
  icon?: string
  phase?: number
}

export function PlaceholderPage({
  title,
  description,
  icon = '🚧',
  phase = 2,
}: PlaceholderPageProps) {
  return (
    <div className="p-6 flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-md space-y-4">
        <span className="text-5xl" aria-hidden="true">{icon}</span>
        <h2 className="text-xl font-bold text-gray-200">{title}</h2>
        <p className="text-sm text-gray-500">{description}</p>
        <span className="inline-block text-xs bg-shield-900/50 border border-shield-700/40
                         text-shield-400 rounded-full px-3 py-1">
          Implemented in Phase {phase}
        </span>
      </div>
    </div>
  )
}
