"""
Circulation API Routes - JSON endpoints for loans, checkouts, returns
Manages book lending, returns, renewals, and overdue tracking
"""
from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from app import db
from app.models import Loan, LoanStatus, BookCopy, CopyStatus, Member, Permission
from app.utils.serializers import LoanSerializer, ApiResponse

bp = Blueprint('api_circulation', __name__, url_prefix='/api/circulation')


@bp.route('/loans', methods=['GET'])
@login_required
def list_loans():
    """
    Get paginated list of loans (admin/staff only)
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 15)
    - status: Filter by status (ACTIVE, OVERDUE, RETURNED)
    - member_id: Filter by member
    
    Response:
    {
        "success": true,
        "data": {
            "items": [...],
            "pagination": {...}
        }
    }
    """
    try:
        # Check staff permission
        if not (hasattr(current_user, 'can') and current_user.can(Permission.CHECKOUT)):
            return ApiResponse.error('Staff access required', status_code=403)
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 15, type=int), 100)
        
        if page < 1:
            page = 1
        
        # Build query with eager loading
        query = Loan.query.options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff)
        )
        
        # Filter by status
        status_filter = request.args.get('status', '').lower()
        valid_statuses = [status.value for status in LoanStatus]
        if status_filter in valid_statuses:
            query = query.filter(Loan.status == status_filter)
        
        # Filter by member
        member_id = request.args.get('member_id', type=int)
        if member_id:
            query = query.filter(Loan.member_id == member_id)
        
        # Sort by checkout date descending
        query = query.order_by(Loan.checkout_date.desc())
        
        # Get total and paginate
        total = query.count()
        offset = (page - 1) * per_page
        loans = query.offset(offset).limit(per_page).all()
        
        items = [LoanSerializer.to_dict(loan) for loan in loans]
        total_pages = (total + per_page - 1) // per_page
        
        return ApiResponse.success({
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        })
    
    except Exception as e:
        current_app.logger.error(f'List loans error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/loans/<int:loan_id>', methods=['GET'])
@login_required
def get_loan(loan_id):
    """
    Get detailed loan information
    
    Response: {...loan details...}
    """
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.CHECKOUT)):
            return ApiResponse.error('Staff access required', status_code=403)
        
        loan = Loan.query.options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff)
        ).get(loan_id)
        
        if not loan:
            return ApiResponse.error('Loan not found', status_code=404)
        
        return ApiResponse.success(LoanSerializer.to_dict(loan))
    
    except Exception as e:
        current_app.logger.error(f'Get loan error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """
    Process book checkout
    
    Request JSON:
    {
        "barcode": "copy_barcode",
        "member_id": 123,
        "loan_days": 7  (optional, default from config)
    }
    
    Response: {...loan...}
    """
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.CHECKOUT)):
            return ApiResponse.error('Staff access required', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        barcode = data.get('barcode', '').strip()
        member_id = data.get('member_id')
        loan_days = data.get('loan_days', 7)
        
        # Validate inputs
        if not barcode:
            return ApiResponse.error('Barcode required', status_code=400)
        if not member_id:
            return ApiResponse.error('Member ID required', status_code=400)
        if loan_days < 1:
            return ApiResponse.error('Loan days must be >= 1', status_code=400)
        
        # Find copy
        copy = BookCopy.query.filter_by(barcode=barcode).first()
        if not copy:
            return ApiResponse.error('Copy not found', status_code=404)
        
        # Check copy status
        if copy.status != CopyStatus.AVAILABLE.value:
            return ApiResponse.error(f'Copy is not available (status: {copy.status})', status_code=409)
        
        # Find member
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)
        
        if not member.is_active:
            return ApiResponse.error('Member account is inactive', status_code=403)
        
        if not member.can_borrow:
            if member.overdue_loans_count > 0:
                return ApiResponse.error('Member has overdue books', status_code=409)
            return ApiResponse.error('Member has reached maximum loan limit', status_code=409)

        staff_user_id = current_user.id if current_user.__class__.__name__ == 'User' else None

        loan = Loan.create_checkout(
            member_id=member.id,
            copy_id=copy.id,
            user_id=staff_user_id,
            loan_days=loan_days,
        )
        db.session.commit()
        
        # Reload with eager loading
        loan = Loan.query.options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff)
        ).get(loan.id)
        
        return ApiResponse.success(
            LoanSerializer.to_dict(loan),
            message='Book checked out successfully',
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Checkout error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/return', methods=['POST'])
@login_required
def return_book():
    """
    Process book return
    
    Request JSON:
    {
        "loan_id": 123,
        "condition": "good"  (optional: good, fair, damaged)
    }
    """
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.RETURN)):
            return ApiResponse.error('Staff access required', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        loan_id = data.get('loan_id')
        if not loan_id:
            return ApiResponse.error('Loan ID required', status_code=400)
        
        # Find loan
        loan = Loan.query.get(loan_id)
        if not loan:
            return ApiResponse.error('Loan not found', status_code=404)
        
        if loan.status == LoanStatus.RETURNED.value:
            return ApiResponse.error('Loan already returned', status_code=409)
        
        staff_user_id = current_user.id if current_user.__class__.__name__ == 'User' else None
        loan.process_return(user_id=staff_user_id)
        
        # Update copy status
        condition = data.get('condition', 'good').lower()
        if condition == 'damaged':
            loan.copy.status = CopyStatus.DAMAGED.value
        
        if 'condition' in data and data['condition']:
            loan.copy.condition = condition
        
        db.session.commit()
        
        # Reload
        loan = Loan.query.options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff)
        ).get(loan.id)
        
        return ApiResponse.success(
            LoanSerializer.to_dict(loan),
            message='Book returned successfully'
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Return error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/overdue', methods=['GET'])
@login_required
def get_overdue():
    """
    Get all overdue loans
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    
    Response: Paginated list of overdue loans
    """
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.CHECKOUT)):
            return ApiResponse.error('Staff access required', status_code=403)
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        if page < 1:
            page = 1
        
        # Get overdue loans
        query = Loan.query.filter(
            Loan.status == LoanStatus.OVERDUE.value
        ).options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff)
        ).order_by(Loan.due_date)
        
        total = query.count()
        offset = (page - 1) * per_page
        loans = query.offset(offset).limit(per_page).all()
        
        items = [LoanSerializer.to_dict(loan) for loan in loans]
        total_pages = (total + per_page - 1) // per_page
        
        return ApiResponse.success({
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        })
    
    except Exception as e:
        current_app.logger.error(f'Get overdue error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/renew', methods=['POST'])
@bp.route('/loans/<int:loan_id>/renew', methods=['POST'])
@login_required
def renew(loan_id=None):
    """Renew an active loan."""
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.CHECKOUT)):
            return ApiResponse.error('Staff access required', status_code=403)

        data = request.get_json(silent=True) or {}
        loan_id = loan_id or data.get('loan_id')
        if not loan_id:
            return ApiResponse.error('Loan ID required', status_code=400)

        loan = Loan.query.options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff),
        ).get(loan_id)
        if not loan:
            return ApiResponse.error('Loan not found', status_code=404)

        if not loan.can_renew:
            if loan.is_overdue:
                return ApiResponse.error('Cannot renew overdue loan', status_code=409)
            return ApiResponse.error('Maximum renewals reached', status_code=409)

        loan.renew(days=data.get('loan_days'))
        db.session.commit()

        return ApiResponse.success(
            LoanSerializer.to_dict(loan),
            message='Loan renewed successfully',
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Renew error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """
    Get circulation statistics
    
    Response:
    {
        "success": true,
        "data": {
            "total_loans": 150,
            "active_loans": 45,
            "overdue_loans": 3,
            "returned_today": 12
        }
    }
    """
    try:
        total_loans = Loan.query.count()
        active_loans = Loan.query.filter(Loan.status == LoanStatus.ACTIVE.value).count()
        overdue_loans = Loan.query.filter(Loan.status == LoanStatus.OVERDUE.value).count()
        
        # Returned today
        today = datetime.utcnow().date()
        returned_today = Loan.query.filter(
            Loan.status == LoanStatus.RETURNED.value,
            db.func.DATE(Loan.return_date) == today
        ).count()
        
        return ApiResponse.success({
            'total_loans': total_loans,
            'active_loans': active_loans,
            'overdue_loans': overdue_loans,
            'returned_today': returned_today,
        })
    
    except Exception as e:
        current_app.logger.error(f'Get stats error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)

