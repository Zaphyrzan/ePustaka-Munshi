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
  role: string // Administrator | Librarian | Student Assistant | Student
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
  renewals?: number
  member?: { id: number; member_id: string; full_name: string }
  copy?: BookCopy & { book?: Book }
}

export interface CirculationStats {
  active_loans?: number
  overdue_loans?: number
  total_books?: number
  available_copies?: number
  [key: string]: number | undefined
}
