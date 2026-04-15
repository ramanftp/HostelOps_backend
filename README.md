# HostelOps Backend API

A FastAPI-based backend system for hostel management, providing comprehensive APIs for owners to manage hostels, rooms, tenants, and payments.

## Features

- **Owner Management**: Registration, authentication, and profile management
- **Hostel Management**: Create and manage multiple hostels with facilities and banking details
- **Room Management**: Track room types, bed counts, and occupancy
- **Tenant Management**: Manage tenant information, identity verification, and assignments
- **Payment Tracking**: Record and track tenant payments with various payment methods
- **OTP Authentication**: Secure login using phone number and OTP verification
- **JWT Tokens**: Secure API access with token-based authentication

## Project Structure

```
backend/
├── core/
│   ├── config.py          # Application settings and configuration
│   └── database.py        # SQLAlchemy database setup and session management
├── modules/
│   ├── main.py            # FastAPI app initialization and routing
│   └── owner/
│       ├── models.py      # SQLAlchemy models (Owner, Hostel, Room, Tenant, TenantPayment)
│       ├── routes.py      # API endpoints for all operations
│       ├── schemas.py     # Pydantic request/response models
│       ├── security.py    # JWT token handling and authentication
│       └── services.py    # Business logic and database operations
├── alembic/               # Database migration files
├── seed.py                # Demo data seeding script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Prerequisites

- Python 3.11+ or 3.12+
- PostgreSQL database
- Redis (for OTP storage)
- Virtual environment tool (venv recommended)

## Installation

1. **Clone and navigate to the project:**
   ```bash
   cd /backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv pg
   source pg/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the backend directory:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/hostel
   SECRET_KEY=your-super-secret-key-change-in-production
   MSG91_AUTH_KEY=your-msg91-auth-key  # Optional, for SMS OTP
   MSG91_TEMPLATE_ID=your-template-id  # Optional
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0
   ```

5. **Set up the database:**
   ```bash
   # Run migrations
   alembic upgrade head

   # Seed demo data (optional)
   python seed.py
   ```

## Running the Application

```bash
# Activate virtual environment
source pg/bin/activate

# Start the server
uvicorn modules.main:app --host 0.0.0.0 --port 5001 --reload
```

The API will be available at:
- **API Base URL**: http://127.0.0.1:5001
- **API Documentation**: http://127.0.0.1:5001/docs (Swagger UI)
- **Alternative Docs**: http://127.0.0.1:5001/redoc

## API Endpoints

### Authentication
- `POST /auth/send-otp` - Send OTP to phone number
- `POST /auth/verify-otp` - Verify OTP and login
- `POST /auth/logout` - Logout current user

### Owner Management
- `POST /owner/register` - Register new owner
- `GET /owner/owners` - List all owners
- `GET /owner/owners/{owner_id}` - Get owner details with hostels and rooms
- `PUT /owner/owners/{owner_id}` - Update owner information

### Hostel Management
- `GET /owner/hostels` - List all hostels
- `POST /owner/hostels` - Create new hostel
- `GET /owner/hostels/{hostel_id}` - Get hostel details
- `PUT /owner/hostels/{hostel_id}` - Update hostel
- `DELETE /owner/hostels/{hostel_id}` - Delete hostel

### Room Management
- `GET /owner/hostels/{hostel_id}/rooms` - List rooms in a hostel
- `POST /owner/hostels/{hostel_id}/rooms` - Create new room
- `GET /owner/rooms/{room_id}` - Get room details
- `PUT /owner/rooms/{room_id}` - Update room
- `DELETE /owner/rooms/{room_id}` - Delete room

### Tenant Management
- `GET /owner/tenants` - List all tenants
- `GET /owner/hostels/{hostel_id}/tenants` - List tenants in a hostel
- `POST /owner/hostels/{hostel_id}/tenants` - Add new tenant
- `GET /owner/rooms/{room_id}/tenants` - List tenants in a room
- `GET /owner/tenants/{tenant_id}` - Get tenant details
- `PUT /owner/tenants/{tenant_id}` - Update tenant
- `DELETE /owner/tenants/{tenant_id}` - Remove tenant

### Payment Management
- `GET /owner/tenants/{tenant_id}/payments` - List tenant payments
- `POST /owner/tenants/{tenant_id}/payments` - Record new payment
- `GET /owner/payments/{payment_id}` - Get payment details
- `PUT /owner/payments/{payment_id}` - Update payment
- `DELETE /owner/payments/{payment_id}` - Delete payment

## Database Models

### Owner
- Personal information (name, email, phone)
- Address details
- Authentication status

### Hostel
- Basic information (name, description, address)
- Banking details for payments
- Facilities and photos
- Payment preferences (cash/UPI)

### Room
- Room number and type
- Bed count and occupancy tracking

### Tenant
- Personal and contact information
- Identity verification (Aadhaar)
- Room and hostel assignment
- Rent and deposit details

### TenantPayment
- Payment amount and date
- Payment method and transaction ID

## Development

### Running Tests
```bash
# Run with pytest (if tests are added)
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Migration message"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Seeding Data
```bash
python seed.py
```

This creates demo data:
- 5 owners
- 5 hostels (1 per owner)
- 25 rooms (5 per hostel)
- ~10 tenants (based on room availability)
- 30-60 payments (3-6 per tenant)

## Configuration

Key settings in `core/config.py`:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `MSG91_*`: SMS service configuration
- `REDIS_*`: Redis connection settings

## Security

- JWT-based authentication
- OTP verification for login
- Password hashing (if implemented)
- CORS configuration
- Input validation with Pydantic

## Contributing

1. Follow the existing code structure
2. Add proper type hints
3. Include comprehensive error handling
4. Update tests for new features
5. Update this README for API changes

## License

This project is proprietary software for HostelOps.

## API Highlights

- `POST /admin/auth/send-otp` (OTP request)
- `POST /admin/auth/verify-otp` (login)
- `GET /admin/auth/users` (list users)
- `POST /admin/auth/users` (create user)
- `GET /admin/auth/users/{id}`, `PUT /admin/auth/users/{id}`, `DELETE /admin/auth/users/{id}`

## Notes

- On startup, `modules/main.py` includes admin router and root heath endpoint.
- The service uses SQLAlchemy with URL from `core/config.py`.
- This project has minor path cleanup for module import consistency (`modules.*` vs `app.*`).

## Troubleshooting

- If port 8000/8001 already in use, choose `--port 8002` or other free port.
- Ensure Redis is running at configured host/port.
- For PostgreSQL, confirm DB exists and user has permissions.
