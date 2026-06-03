"""
Circulation API Routes - JSON endpoints for loans, checkouts, returns
"""
from flask import Blueprint

bp = Blueprint('api_circulation', __name__, url_prefix='/api/circulation')

# TODO: Implement circulation API endpoints
# - GET /api/circulation/loans
# - GET /api/circulation/loans/:id
# - POST /api/circulation/checkout
# - POST /api/circulation/return
# - POST /api/circulation/renew
# - GET /api/circulation/overdue
# - GET /api/circulation/stats
