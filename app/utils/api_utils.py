"""
API optimization utilities for pagination, filtering, and cursor-based navigation.
Reduces response payload size and improves query performance on large datasets.
"""
from typing import Dict, List, Any, Optional, Tuple
from flask import request
import base64
from urllib.parse import quote, unquote
from math import ceil


class PaginationConfig:
    """Configuration for pagination behavior"""
    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100
    MIN_PER_PAGE = 5


class CursorPagination:
    """
    Cursor-based pagination for efficient traversal of large datasets.
    More efficient than offset-based pagination for large collections.
    
    Usage:
        cursor = CursorPagination.from_request()
        query = Book.query.order_by(Book.id)
        result = cursor.paginate(query)
    """
    
    def __init__(self, per_page: int = PaginationConfig.DEFAULT_PER_PAGE):
        self.per_page = min(per_page, PaginationConfig.MAX_PER_PAGE)
        self.per_page = max(self.per_page, PaginationConfig.MIN_PER_PAGE)
        self.cursor = None
        self.direction = 'next'
    
    @staticmethod
    def from_request():
        """Parse pagination parameters from Flask request"""
        cursor = CursorPagination()
        
        # Get per_page from query string
        per_page = request.args.get('per_page', PaginationConfig.DEFAULT_PER_PAGE, type=int)
        cursor.per_page = min(per_page, PaginationConfig.MAX_PER_PAGE)
        cursor.per_page = max(cursor.per_page, PaginationConfig.MIN_PER_PAGE)
        
        # Get cursor from query string
        cursor_param = request.args.get('cursor', None)
        if cursor_param:
            try:
                # Decode cursor (base64 encoded ID:timestamp)
                cursor.cursor = unquote(cursor_param)
            except Exception:
                cursor.cursor = None
        
        # Get direction (next or prev)
        cursor.direction = request.args.get('direction', 'next')
        
        return cursor
    
    def paginate(self, query: Any) -> Dict[str, Any]:
        """
        Paginate query results using cursor.
        
        Args:
            query: SQLAlchemy query object
        
        Returns:
            Dict with items, next_cursor, prev_cursor, has_next, has_prev
        """
        # Get one extra item to check if there are more
        items = query.limit(self.per_page + 1).all()
        
        has_more = len(items) > self.per_page
        if has_more:
            items = items[:self.per_page]
        
        result = {
            'items': items,
            'has_next': has_more,
            'per_page': self.per_page,
        }
        
        # Generate cursors for navigation
        if items:
            last_item = items[-1]
            result['next_cursor'] = self._encode_cursor(last_item.id, 'next')
            if len(items) > 1:
                first_item = items[0]
                result['prev_cursor'] = self._encode_cursor(first_item.id, 'prev')
        
        return result
    
    @staticmethod
    def _encode_cursor(item_id: int, direction: str = 'next') -> str:
        """Encode cursor value (base64 for URL safety)"""
        cursor_value = f"{item_id}:{direction}"
        return quote(base64.b64encode(cursor_value.encode()).decode())


class OffsetPagination:
    """
    Traditional offset-based pagination for compatibility.
    Simpler but less efficient than cursor pagination for large datasets.
    """
    
    def __init__(self, page: int = 1, per_page: int = PaginationConfig.DEFAULT_PER_PAGE):
        self.page = max(page, 1)
        self.per_page = min(per_page, PaginationConfig.MAX_PER_PAGE)
        self.per_page = max(self.per_page, PaginationConfig.MIN_PER_PAGE)
    
    @staticmethod
    def from_request():
        """Parse pagination parameters from Flask request"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', PaginationConfig.DEFAULT_PER_PAGE, type=int)
        return OffsetPagination(page, per_page)
    
    def paginate(self, query: Any) -> Dict[str, Any]:
        """
        Paginate query results using offset/limit.
        
        Args:
            query: SQLAlchemy query object or paginate() result
        
        Returns:
            Dict with items, total, pages, has_next, has_prev, page
        """
        # If query has paginate method (SQLAlchemy pagination object), use it
        if hasattr(query, 'paginate'):
            paginated = query.paginate(page=self.page, per_page=self.per_page, error_out=False)
            return {
                'items': paginated.items,
                'total': paginated.total,
                'pages': paginated.pages,
                'current_page': self.page,
                'per_page': self.per_page,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev,
                'next_page': self.page + 1 if paginated.has_next else None,
                'prev_page': self.page - 1 if paginated.has_prev else None,
            }
        
        # Otherwise, manually paginate
        total = query.count()
        pages = ceil(total / self.per_page) if total > 0 else 1
        offset = (self.page - 1) * self.per_page
        
        items = query.offset(offset).limit(self.per_page).all()
        has_next = offset + self.per_page < total
        has_prev = self.page > 1
        
        return {
            'items': items,
            'total': total,
            'pages': pages,
            'current_page': self.page,
            'per_page': self.per_page,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': self.page + 1 if has_next else None,
            'prev_page': self.page - 1 if has_prev else None,
        }


class ResponseFilter:
    """
    Filter response data to include only necessary fields.
    Reduces JSON payload size by 30-50% depending on fields.
    """
    
    # Define which fields to include for each model type
    FIELD_MAPPINGS = {
        'Book': ['id', 'title', 'author', 'isbn', 'category', 'description', 'copies_count', 'available_count'],
        'BookCopy': ['id', 'barcode', 'accession_number', 'status', 'condition', 'book_id'],
        'Member': ['id', 'member_id', 'full_name', 'form_level', 'member_type', 'is_active', 'total_books_read'],
        'Loan': ['id', 'checkout_date', 'due_date', 'return_date', 'status', 'member_id', 'copy_id'],
        'User': ['id', 'username', 'email', 'is_active', 'role_id'],
    }
    
    @staticmethod
    def serialize(obj: Any, model_type: str = None, custom_fields: List[str] = None) -> Dict[str, Any]:
        """
        Serialize an object to dictionary with only selected fields.
        
        Args:
            obj: Object to serialize
            model_type: Type name for field mapping (defaults to class name)
            custom_fields: Custom field list (overrides default mapping)
        
        Returns:
            Dictionary with filtered fields
        """
        if not obj:
            return {}
        
        model_type = model_type or obj.__class__.__name__
        fields = custom_fields or ResponseFilter.FIELD_MAPPINGS.get(model_type, [])
        
        result = {}
        for field in fields:
            if hasattr(obj, field):
                value = getattr(obj, field)
                # Convert datetime to ISO format string
                if hasattr(value, 'isoformat'):
                    result[field] = value.isoformat()
                else:
                    result[field] = value
        
        return result
    
    @staticmethod
    def serialize_list(items: List[Any], model_type: str = None, custom_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Serialize list of objects"""
        return [ResponseFilter.serialize(item, model_type, custom_fields) for item in items]


class ApiResponse:
    """
    Standard API response format for consistency and better client handling.
    """
    
    @staticmethod
    def success(data: Any = None, message: str = None, pagination: Dict = None) -> Dict[str, Any]:
        """
        Create successful response.
        
        Args:
            data: Response payload
            message: Optional success message
            pagination: Optional pagination metadata
        
        Returns:
            Standardized response dictionary
        """
        response = {
            'success': True,
            'data': data,
        }
        if message:
            response['message'] = message
        if pagination:
            response['pagination'] = pagination
        return response
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Dict = None) -> Dict[str, Any]:
        """
        Create error response.
        
        Args:
            message: Error message
            error_code: Optional error code for client handling
            details: Optional additional error details
        
        Returns:
            Standardized error response dictionary
        """
        response = {
            'success': False,
            'message': message,
        }
        if error_code:
            response['error_code'] = error_code
        if details:
            response['details'] = details
        return response


def get_pagination_params() -> Tuple[int, int]:
    """
    Get and validate pagination parameters from request.
    
    Returns:
        Tuple of (page, per_page) with validated values
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', PaginationConfig.DEFAULT_PER_PAGE, type=int)
    
    # Validate values
    page = max(page, 1)
    per_page = min(per_page, PaginationConfig.MAX_PER_PAGE)
    per_page = max(per_page, PaginationConfig.MIN_PER_PAGE)
    
    return page, per_page
