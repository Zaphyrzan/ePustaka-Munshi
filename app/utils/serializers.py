"""
Model Serializers - Convert SQLAlchemy models to dictionaries for JSON responses
Provides consistent serialization across all API endpoints
"""
from datetime import datetime
from typing import Dict, Any, List

from flask import current_app


class ModelSerializer:
    """Base serializer for converting models to dictionaries"""
    
    @staticmethod
    def serialize_datetime(dt: datetime) -> str:
        """Convert datetime to ISO format string"""
        if not dt:
            return None
        return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    
    @staticmethod
    def serialize_enum(enum_val) -> str:
        """Convert enum to string value"""
        if hasattr(enum_val, 'value'):
            return enum_val.value
        return str(enum_val) if enum_val else None


class UserSerializer(ModelSerializer):
    """Serialize User model"""
    
    @staticmethod
    def to_dict(user, include_password=False) -> Dict[str, Any]:
        """
        Convert User to dictionary
        
        Args:
            user: User model instance
            include_password: Whether to include password_hash (default: False)
        
        Returns:
            Dictionary with user data
        """
        if not user:
            return None
        
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'role': {
                'id': user.role.id,
                'name': user.role.name,
                'permissions': user.role.permissions
            } if user.role else None,
            'created_at': ModelSerializer.serialize_datetime(user.created_at),
            'updated_at': ModelSerializer.serialize_datetime(user.updated_at),
            'last_login': ModelSerializer.serialize_datetime(user.last_login),
        }
        
        if include_password:
            data['password_hash'] = user.password_hash

        return data

    @staticmethod
    def to_summary_dict(user) -> Dict[str, Any]:
        """Lightweight payload for embedding in other resources.
        Runs no extra queries (role is not loaded)."""
        if not user:
            return None

        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
        }


class MemberSerializer(ModelSerializer):
    """Serialize Member model"""
    
    @staticmethod
    def to_dict(member, include_password=False) -> Dict[str, Any]:
        """
        Convert Member to dictionary
        
        Args:
            member: Member model instance
            include_password: Whether to include password_hash (default: False)
        
        Returns:
            Dictionary with member data
        """
        if not member:
            return None

        # Use batch-annotated counts when present (see users_api) to avoid
        # per-member COUNT queries on list endpoints.
        active_loans = getattr(member, '_active_loans', None)
        overdue_loans = getattr(member, '_overdue_loans', None)
        if active_loans is None:
            active_loans = member.active_loans_count
        if overdue_loans is None:
            overdue_loans = member.overdue_loans_count

        # Mirrors Member.can_borrow, but on the precomputed counts.
        max_loans = current_app.config.get('MAX_LOANS_PER_MEMBER', 5)
        can_borrow = (
            bool(member.is_active)
            and active_loans < max_loans
            and overdue_loans == 0
        )

        data = {
            'id': member.id,
            'member_id': member.member_id,
            'full_name': member.full_name,
            'email': member.email,
            'phone': member.phone,
            'member_type': member.member_type,
            'form_level': member.form_level,
            'form_name': member.form_name,
            'class_group': member.class_group,
            'student_year': member.student_year,
            'total_books_read': member.total_books_read,
            'is_active': member.is_active,
            'is_staff': member.is_staff,
            'is_graduated': member.is_graduated,
            'mark_for_deletion': member.mark_for_deletion,
            'active_loans': active_loans,
            'overdue_loans': overdue_loans,
            'can_borrow': can_borrow,
            'created_at': ModelSerializer.serialize_datetime(member.created_at),
            'updated_at': ModelSerializer.serialize_datetime(member.updated_at),
            'last_login': ModelSerializer.serialize_datetime(member.last_login),
            'notes': member.notes,
        }
        
        if include_password:
            data['password_hash'] = member.password_hash

        return data

    @staticmethod
    def to_summary_dict(member) -> Dict[str, Any]:
        """Lightweight payload for embedding in other resources.
        Runs no extra queries (no loan counts)."""
        if not member:
            return None

        return {
            'id': member.id,
            'member_id': member.member_id,
            'full_name': member.full_name,
            'member_type': member.member_type,
            'form_level': member.form_level,
            'form_name': member.form_name,
            'class_group': member.class_group,
            'is_active': member.is_active,
        }


class BookSerializer(ModelSerializer):
    """Serialize Book model"""
    
    @staticmethod
    def to_dict(book, include_copies=False) -> Dict[str, Any]:
        """
        Convert Book to dictionary
        
        Args:
            book: Book model instance
            include_copies: Whether to include BookCopy relationships (default: False)
        
        Returns:
            Dictionary with book data
        """
        if not book:
            return None
        
        total_copies = getattr(book, '_total_copies', None)
        available_copies = getattr(book, '_available_copies', None)
        if total_copies is None:
            total_copies = book.total_copies
        if available_copies is None:
            available_copies = book.available_copies

        data = {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'publisher': book.publisher,
            'publication_year': book.publication_year,
            'edition': book.edition,
            'category': book.category,
            'call_number': book.call_number,
            'subject': book.subject,
            'language': book.language,
            'description': book.description,
            'page_count': book.page_count,
            'cover_image': book.cover_image,
            'price': book.price,
            'total_copies': total_copies,
            'available_copies': available_copies,
            'is_available': available_copies > 0,
            'created_at': ModelSerializer.serialize_datetime(book.created_at),
            'updated_at': ModelSerializer.serialize_datetime(book.updated_at),
        }
        
        if include_copies:
            data['copies'] = [
                BookCopySerializer.to_dict(copy)
                for copy in book.copies.all()
            ]

        return data

    @staticmethod
    def to_summary_dict(book) -> Dict[str, Any]:
        """Lightweight payload for embedding in other resources.
        Runs no extra queries (no copy counts)."""
        if not book:
            return None

        return {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
            'category': book.category,
            'call_number': book.call_number,
            'cover_image': book.cover_image,
        }


class BookCopySerializer(ModelSerializer):
    """Serialize BookCopy model"""
    
    @staticmethod
    def to_dict(copy, include_book=True) -> Dict[str, Any]:
        """
        Convert BookCopy to dictionary
        
        Args:
            copy: BookCopy model instance
            include_book: Whether to include Book data (default: True)
        
        Returns:
            Dictionary with copy data
        """
        if not copy:
            return None
        
        data = {
            'id': copy.id,
            'barcode': copy.barcode,
            'accession_number': copy.accession_number,
            'status': copy.status,
            'location': copy.location,
            'condition': copy.condition,
            'acquisition_date': ModelSerializer.serialize_datetime(copy.acquisition_date),
            'notes': copy.notes,
            'created_at': ModelSerializer.serialize_datetime(copy.created_at),
        }
        
        if include_book and copy.book:
            data['book'] = BookSerializer.to_dict(copy.book, include_copies=False)
        else:
            data['book_id'] = copy.book_id

        return data

    @staticmethod
    def to_summary_dict(copy) -> Dict[str, Any]:
        """Lightweight payload for embedding in loans.
        Runs no extra queries (book is summarized without copy counts)."""
        if not copy:
            return None

        return {
            'id': copy.id,
            'barcode': copy.barcode,
            'accession_number': copy.accession_number,
            'status': copy.status,
            'location': copy.location,
            'condition': copy.condition,
            'book': BookSerializer.to_summary_dict(copy.book),
        }


class LoanSerializer(ModelSerializer):
    """Serialize Loan model"""
    
    @staticmethod
    def to_dict(loan, include_relations=True) -> Dict[str, Any]:
        """
        Convert Loan to dictionary
        
        Args:
            loan: Loan model instance
            include_relations: Whether to include Book/Member/User data (default: True)
        
        Returns:
            Dictionary with loan data
        """
        if not loan:
            return None
        
        # Effective status: the stored status only flips to 'overdue' when the
        # manual update-overdue action runs, so compute it live instead of
        # trusting the stale column.
        status = loan.status
        if status == 'active' and loan.is_overdue:
            status = 'overdue'

        data = {
            'id': loan.id,
            'status': status,
            'checkout_date': ModelSerializer.serialize_datetime(loan.checkout_date),
            'due_date': ModelSerializer.serialize_datetime(loan.due_date),
            'return_date': ModelSerializer.serialize_datetime(loan.return_date),
            'is_overdue': loan.is_overdue,
            'days_overdue': loan.days_overdue,
            'renewal_count': loan.renewal_count,
            'can_renew': loan.can_renew,
            'fine_amount': loan.fine_amount,
            'fine_paid': loan.fine_paid,
            'notes': loan.notes,
        }

        if loan.due_date and loan.status != 'returned':
            remaining = loan.due_date - datetime.utcnow()
            data['days_remaining'] = max(remaining.days, 0)
        else:
            data['days_remaining'] = 0
        
        if include_relations:
            data['copy'] = BookCopySerializer.to_summary_dict(loan.copy)
            data['member'] = MemberSerializer.to_summary_dict(loan.member)
            data['checkout_staff'] = UserSerializer.to_summary_dict(loan.checkout_staff)
            data['return_staff'] = UserSerializer.to_summary_dict(loan.return_staff)
        else:
            data['copy_id'] = loan.copy_id
            data['member_id'] = loan.member_id
            data['checkout_staff_id'] = loan.checkout_by
            data['return_staff_id'] = loan.return_by
        
        return data


class OCRJobSerializer(ModelSerializer):
    """Serialize OCRJob model"""
    
    @staticmethod
    def to_dict(job, include_results=False) -> Dict[str, Any]:
        """
        Convert OCRJob to dictionary
        
        Args:
            job: OCRJob model instance
            include_results: Whether to include OCR results (can be large) (default: False)
        
        Returns:
            Dictionary with OCR job data
        """
        if not job:
            return None
        
        data = {
            'id': job.id,
            'job_name': job.job_name,
            'source_type': job.source_type,
            'original_filename': job.original_filename,
            'status': job.status,
            'progress': job.progress,
            'page_count': job.page_count,
            'result_count': job.result_count,
            'reviewed_count': job.reviewed_count,
            'pending_review_count': job.pending_review_count,
            'created_at': ModelSerializer.serialize_datetime(job.created_at),
            'started_at': ModelSerializer.serialize_datetime(job.started_at),
            'completed_at': ModelSerializer.serialize_datetime(job.completed_at),
            'reviewed_at': ModelSerializer.serialize_datetime(job.reviewed_at),
            'committed_at': ModelSerializer.serialize_datetime(job.committed_at),
            'created_by': job.created_by,
            'reviewed_by': job.reviewed_by,
            'error_message': job.error_message,
        }
        
        if include_results:
            data['results'] = [
                result.to_dict()
                for result in sorted(
                    job.results.all(),
                    key=lambda result: (result.page_number or 0, result.row_number or 0)
                )
            ]
        else:
            data['has_results'] = job.result_count > 0
        
        return data


class PaginationSerializer:
    """Serialize paginated results"""
    
    @staticmethod
    def to_dict(items: List[Any], page: int, per_page: int, total: int, 
                serializer_func=None) -> Dict[str, Any]:
        """
        Convert paginated results to dictionary
        
        Args:
            items: List of items on current page
            page: Current page number (1-based)
            per_page: Items per page
            total: Total number of items
            serializer_func: Function to serialize each item (optional)
        
        Returns:
            Dictionary with pagination data
        """
        total_pages = (total + per_page - 1) // per_page
        
        # Serialize items if serializer function provided
        serialized_items = items
        if serializer_func:
            serialized_items = [serializer_func(item) for item in items]
        
        return {
            'items': serialized_items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        }


# Response wrapper for consistent API responses
class ApiResponse:
    """Consistent API response format"""
    
    @staticmethod
    def success(data: Any = None, message: str = 'Success', 
                status_code: int = 200) -> Dict[str, Any]:
        """
        Create successful response
        
        Args:
            data: Response data (optional)
            message: Response message
            status_code: HTTP status code
        
        Returns:
            Dictionary with response format
        """
        return {
            'success': True,
            'message': message,
            'data': data,
            'status_code': status_code,
        }, status_code
    
    @staticmethod
    def error(message: str, data: Any = None, 
              status_code: int = 400) -> Dict[str, Any]:
        """
        Create error response
        
        Args:
            message: Error message
            data: Additional error data (optional)
            status_code: HTTP status code
        
        Returns:
            Dictionary with error response format
        """
        return {
            'success': False,
            'message': message,
            'data': data,
            'status_code': status_code,
        }, status_code
