/** A clickable, sortable table column header (shared by Users and Catalog). */
export default function SortHeader({
  label,
  field,
  sort,
  order,
  onSort,
  className,
}: {
  label: string
  field: string
  sort: string
  order: 'asc' | 'desc'
  onSort: (field: string) => void
  className?: string
}) {
  const active = sort === field
  return (
    <th className={className} style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => onSort(field)}>
      {label}{' '}
      {active ? (
        <i className={`bi bi-caret-${order === 'asc' ? 'up' : 'down'}-fill small`} />
      ) : (
        <i className="bi bi-arrow-down-up small text-muted opacity-50" />
      )}
    </th>
  )
}
