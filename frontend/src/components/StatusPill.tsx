type StatusPillProps = {
  online: boolean | null
}

export function StatusPill({ online }: StatusPillProps) {
  const label =
    online === null ? 'Checking API…' : online ? 'API online' : 'API offline'

  return (
    <div
      className={`status-pill${online === true ? ' status-pill--ok' : ''}${online === false ? ' status-pill--error' : ''}`}
      role="status"
    >
      <span className="status-pill__dot" aria-hidden />
      {label}
    </div>
  )
}
