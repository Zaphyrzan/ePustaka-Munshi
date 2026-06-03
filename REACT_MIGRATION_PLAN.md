# ePustaka-Munshi React Migration Plan

## Phase Overview

This document outlines the systematic migration from Flask (server-side templates) to React (SPA) architecture.

---

## PHASE 1: Audit & Planning (Complete)

### Codebase Structure Audit
- ✅ Models: 5 core models (User, Role, Member, Book, BookCopy, Loan, OCRJob)
- ✅ Routes: 7 blueprints (main, auth, catalog, circulation, users, student, ocr)
- ✅ Services: OCR, scanner, barcode utilities
- ✅ Database: PostgreSQL (Supabase pooler on Vercel, SQLite local)
- ✅ Dependencies: Flask 3.0, SQLAlchemy 2.0.49, Flask-Login, Werkzeug 3.0

### Backend Changes Needed
1. Convert all routes to JSON API responses
2. Add CORS support
3. Add JSON request/response serializers
4. Implement JWT tokens (optional, keep Flask-Login for now)
5. Add error handling middleware

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast, modern, ~50% faster than Create React App)
- **State Management**: Zustand (lightweight) or React Context
- **API Client**: Axios with interceptors
- **Routing**: React Router v6
- **UI Component**: Shadcn/ui or Material-UI (bilingual support needed)
- **Internationalization**: i18next (already needed for EN/BM)

### Data Flow
```
User Input (React) → API Request → Flask Route → Database → JSON Response → React State → UI Render
```

---

## PHASE 2: Backend Preparation

### 2.1 Add JSON API Layer
- Create `app/api/` directory for new JSON endpoints
- Keep Flask-Login for session-based auth (backward compatible)
- Add response serializers for all models

### 2.2 Setup CORS & Middleware
- Enable CORS on Vercel deployment
- Add JSON error handler
- Add request/response logging

### 2.3 Endpoint Mapping
#### Auth Routes
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me (current user)
- POST /api/auth/register
- POST /api/auth/change-password

#### Catalog Routes
- GET /api/books (paginated, searchable)
- GET /api/books/:id
- POST /api/books (create)
- PUT /api/books/:id (edit)
- DELETE /api/books/:id
- GET /api/books/:id/copies
- GET /api/categories

#### Circulation Routes
- GET /api/loans (paginated)
- GET /api/loans/:id
- POST /api/circulation/checkout
- POST /api/circulation/return
- POST /api/circulation/renew
- GET /api/circulation/overdue
- GET /api/circulation/stats

#### Member/User Routes
- GET /api/members (paginated)
- GET /api/members/:id
- POST /api/members (create)
- PUT /api/members/:id (edit)
- GET /api/users (staff, admin)
- POST /api/users (create)

#### Student Portal
- GET /api/student/dashboard
- GET /api/student/loans
- GET /api/student/search
- GET /api/student/leaderboard

#### OCR Routes
- POST /api/ocr/upload
- GET /api/ocr/jobs
- GET /api/ocr/jobs/:id
- POST /api/ocr/jobs/:id/approve
- POST /api/ocr/import

---

## PHASE 3: Frontend Setup

### 3.1 Create React App with Vite
- Initialize with TypeScript template
- Setup environment variables (.env.local, .env.production)
- Configure API base URL for dev/prod

### 3.2 Project Structure
```
frontend/
├── src/
│   ├── api/            # API client calls
│   ├── components/     # Reusable UI components
│   ├── pages/         # Page components
│   ├── hooks/         # Custom React hooks
│   ├── store/         # State management (Zustand)
│   ├── types/         # TypeScript interfaces
│   ├── utils/         # Helper functions
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 3.3 Core Components to Build
1. **Layout**: Navbar, Sidebar, Footer (bilingual)
2. **Auth**: Login/Register, Profile, ChangePassword
3. **Catalog**: BookList, BookDetail, BookSearch, CategoryFilter
4. **Circulation**: CheckoutForm, ReturnForm, LoanHistory
5. **Student Portal**: Dashboard, MyLoans, SearchBooks, Leaderboard
6. **Admin**: MemberList, UserManagement, Statistics
7. **OCR**: Upload, ReviewJob, ApprovalPanel

---

## PHASE 4: Component Migration Order

### Priority 1: Core Pages (Week 1)
1. Login/Auth pages
2. Dashboard
3. Search/Catalog
4. User profile

### Priority 2: Main Features (Week 2)
1. Circulation (checkout/return)
2. Loan history
3. Member management
4. Overdue tracking

### Priority 3: Admin Features (Week 3)
1. Staff management
2. User roles
3. Statistics
4. System settings

### Priority 4: OCR & Advanced (Week 4)
1. OCR upload & review
2. Import functionality
3. Advanced search
4. Leaderboard (student)

---

## PHASE 5: Deployment Strategy

### Testing
1. Local development (React dev server + Flask backend)
2. Build and test production bundle
3. Load testing with Lighthouse

### Deployment Options

**Option A: Monorepo (Flask + React in same Vercel deployment)**
- Single deployment
- Simpler CORS
- Shared environment variables

**Option B: Separate Deployments (Recommended)**
- Flask API on Vercel
- React SPA on Vercel/Netlify/GitHub Pages
- Independent scaling
- Easier to manage

### Environment Setup
```
.env.local
├── VITE_API_URL=http://localhost:5000
├── VITE_APP_NAME=ePustaka-Munshi

.env.production
├── VITE_API_URL=https://api.epustaka.vercel.app
├── VITE_APP_NAME=ePustaka-Munshi
```

---

## Code Quality Standards

### TypeScript Usage
- Strict mode enabled
- All components typed
- No `any` types without justification
- Interfaces for all API responses

### Component Structure
```typescript
// Good component structure
const BookList: React.FC<BookListProps> = ({ category, onSelect }) => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Fetch logic
  }, [category]);
  
  return (
    // JSX
  );
};

export default BookList;
```

### No Spaghetti Code Rules
1. Single Responsibility: Each component does one thing
2. Proper abstractions: Custom hooks for shared logic
3. Clean imports: No circular dependencies
4. Constants: No magic strings/numbers
5. Error handling: Try-catch, error boundaries
6. Comments: Document WHY, not WHAT

### Performance Optimization
- React.memo for pure components
- useMemo for expensive computations
- Code splitting by route
- Lazy loading images
- Caching API responses

---

## File-by-File Checklist

### Backend Routes to Convert
- [ ] auth.py → /api/auth endpoints
- [ ] catalog.py → /api/catalog endpoints
- [ ] circulation.py → /api/circulation endpoints
- [ ] users.py → /api/users endpoints
- [ ] student.py → /api/student endpoints
- [ ] ocr.py → /api/ocr endpoints
- [ ] main.py → /api/main endpoints (health, stats)

### Models to Serialize
- [ ] User.to_dict()
- [ ] Role.to_dict()
- [ ] Member.to_dict()
- [ ] Book.to_dict()
- [ ] BookCopy.to_dict()
- [ ] Loan.to_dict()
- [ ] OCRJob.to_dict()

### React Components to Create (64 total)
- [ ] Layout: 5 components
- [ ] Auth: 6 components
- [ ] Catalog: 8 components
- [ ] Circulation: 6 components
- [ ] Student: 10 components
- [ ] Admin: 15 components
- [ ] OCR: 8 components
- [ ] Common/Utils: 6 components

---

## Success Criteria

### Performance
- ✅ Time to Interactive: < 2 seconds
- ✅ Largest Contentful Paint: < 2.5 seconds
- ✅ API Response Time: < 500ms
- ✅ Lighthouse Score: > 90

### Functionality
- ✅ All Flask routes working as JSON APIs
- ✅ All React pages render correctly
- ✅ User authentication flow works
- ✅ OCR processing works as before
- ✅ Database operations unchanged
- ✅ Multilingual support (EN/BM)

### Code Quality
- ✅ TypeScript strict mode passes
- ✅ No console errors/warnings
- ✅ Proper error handling throughout
- ✅ All components have comments
- ✅ No code duplication
- ✅ Proper git commit messages

---

## Next Steps

1. **Backend Phase (2-3 days)**
   - Create /api routes
   - Add serializers
   - Test all endpoints

2. **Frontend Setup (1 day)**
   - Initialize React+Vite
   - Setup project structure
   - Configure tooling

3. **Component Development (3-4 weeks)**
   - Build by priority
   - Integration testing
   - Performance optimization

4. **Deployment (1 week)**
   - Environment setup
   - Testing on staging
   - Production deployment

---

## Notes
- Keep Flask-Login for backward compatibility during migration
- Database schema unchanged
- OCR functionality unchanged (still works locally + uploads to Supabase)
- Can run both Flask and React in parallel during development
- Git branch: `react-migration` for all work
