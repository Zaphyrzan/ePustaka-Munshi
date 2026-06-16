// Shapes returned by the Flask JSON API (app/utils/serializers.py)

export interface AuthUser {
  id: number
  username?: string // staff
  member_id?: string // students
  email?: string
  full_name?: string
}

export interface AuthSession {
  user: AuthUser
  role: string // Administrator | Librarian | Library Prefect | Student
  user_type: 'staff' | 'student'
}

export interface Book {
  id: number
  title: string
  author?: string
  isbn?: string
  publisher?: string
  publication_year?: number
  category?: string
  call_number?: string
  language?: string
  description?: string
  page_count?: number
  price?: number
  total_copies?: number
  available_copies?: number
  copies?: BookCopy[]
}

export interface BookCopy {
  id: number
  barcode?: string
  accession_number: string
  status: string
  condition?: string
  location?: string
  book_id: number
}

export interface Loan {
  id: number
  loan_date?: string
  due_date?: string
  return_date?: string
  status: string
  is_overdue?: boolean
  days_overdue?: number
  days_remaining?: number
  renewals?: number
  member?: { id: number; member_id: string; full_name: string; form_name?: string; class_group?: string }
  copy?: BookCopy & { book?: Book }
  checkout_staff?: { id: number; username?: string; full_name?: string } | null
  return_staff?: { id: number; username?: string; full_name?: string } | null
}

/** Human status for a loan: overdue beats due-soon beats plain status */
export function loanBadge(loan: Loan): { label: string; className: string } {
  if (loan.status === 'returned') return { label: 'returned', className: 'bg-secondary' }
  if (loan.is_overdue || loan.status === 'overdue') {
    const days = loan.days_overdue ?? 0
    return { label: days > 0 ? `${days} day${days === 1 ? '' : 's'} overdue` : 'overdue', className: 'bg-danger' }
  }
  const left = loan.days_remaining
  if (left != null && left <= 3) {
    return { label: left === 0 ? 'due today' : `due in ${left} day${left === 1 ? '' : 's'}`, className: 'bg-warning text-dark' }
  }
  return { label: loan.status, className: 'bg-info text-dark' }
}

export interface CirculationStats {
  active_loans?: number
  overdue_loans?: number
  total_books?: number
  available_copies?: number
  [key: string]: number | undefined
}
