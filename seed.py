"""
Demo data seeding script for HostelOps backend
Generates sample records for all models: Owner, Hostel, Room, Tenant
"""
import sys
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, '/home/raman/hostelapp/HostelOps_backend/backend')

from core.database import SessionLocal, engine, Base
from modules.owner.models import Owner, Hostel, Room, Tenant, RoomType


def seed_owners(db: Session):
    """Create 5 demo owner records"""
    owners_data = [
        {
            "phone_number": "+919876543210",
            "first_name": "Rajesh",
            "last_name": "Kumar",
            "email": "rajesh.kumar@email.com",
            "status": "active",
            "area": "Sector 5",
            "street_1": "Main Street 123",
            "street_2": "Near Market",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "zipcode": "110001",
        },
        {
            "phone_number": "+919876543211",
            "first_name": "Priya",
            "last_name": "Singh",
            "email": "priya.singh@email.com",
            "status": "active",
            "area": "Koramangala",
            "street_1": "5th Block 456",
            "street_2": "Opposite Park",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "zipcode": "560034",
        },
        {
            "phone_number": "+919876543212",
            "first_name": "Amit",
            "last_name": "Patel",
            "email": "amit.patel@email.com",
            "status": "active",
            "area": "Bandra",
            "street_1": "Marine Drive 789",
            "street_2": "Near Beach",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "zipcode": "400050",
        },
        {
            "phone_number": "+919876543213",
            "first_name": "Sneha",
            "last_name": "Gupta",
            "email": "sneha.gupta@email.com",
            "status": "active",
            "area": "Indiranagar",
            "street_1": "100 Feet Road 321",
            "street_2": "Opposite School",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "zipcode": "560038",
        },
        {
            "phone_number": "+919876543214",
            "first_name": "Vikram",
            "last_name": "Sharma",
            "email": "vikram.sharma@email.com",
            "status": "active",
            "area": "Sector 7",
            "street_1": "Avenue Road 654",
            "street_2": "Near Hospital",
            "city": "Gurgaon",
            "state": "Haryana",
            "country": "India",
            "zipcode": "122001",
        },
    ]
    
    owners = []
    for data in owners_data:
        # Check if owner already exists
        existing = db.query(Owner).filter(Owner.phone_number == data["phone_number"]).first()
        if not existing:
            owner = Owner(**data)
            db.add(owner)
            owners.append(owner)
    
    db.commit()
    print(f"✓ Created {len(owners)} demo owner records")
    return owners


def seed_hostels(db: Session):
    """Create 5 demo hostel records linked to owners"""
    owners = db.query(Owner).all()
    if not owners:
        print("No owners found. Please seed owners first.")
        return []
    
    hostels_data = [
        {
            "owner_id": owners[0].id,
            "name": "Travelers Haven",
            "description": "Budget-friendly hostel in city center with great atmosphere",
            "address": "Main Street 123",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "zipcode": "110001",
            "photos_urls": ["https://example.com/hostel1_1.jpg", "https://example.com/hostel1_2.jpg"],
            "bank_account_number": "1234567890123456",
            "bank_ifsc_code": "SBIN0001234",
            "bank_name": "State Bank of India",
            "bank_account_holder_name": "Rajesh Kumar",
            "upi_id": "rajesh.kumar@upi",
            "is_cash": True,
            "facilities": ["WiFi", "Kitchen", "Laundry", "Common Area", "24/7 Security"],
        },
        {
            "owner_id": owners[1].id,
            "name": "Garden View Hostel",
            "description": "Peaceful hostel with garden views and modern amenities",
            "address": "5th Block 456",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "zipcode": "560034",
            "photos_urls": ["https://example.com/hostel2_1.jpg", "https://example.com/hostel2_2.jpg"],
            "bank_account_number": "2345678901234567",
            "bank_ifsc_code": "SBIN0002345",
            "bank_name": "State Bank of India",
            "bank_account_holder_name": "Priya Singh",
            "upi_id": "priya.singh@upi",
            "is_cash": True,
            "facilities": ["WiFi", "Yoga Class", "Garden", "Lounge", "Breakfast Included"],
        },
        {
            "owner_id": owners[2].id,
            "name": "Beachside Backpackers",
            "description": "Vibrant hostel near beach with party atmosphere",
            "address": "Marine Drive 789",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "zipcode": "400050",
            "photos_urls": ["https://example.com/hostel3_1.jpg", "https://example.com/hostel3_2.jpg"],
            "bank_account_number": "3456789012345678",
            "bank_ifsc_code": "HDFC0001234",
            "bank_name": "HDFC Bank",
            "bank_account_holder_name": "Amit Patel",
            "upi_id": "amit.patel@upi",
            "is_cash": True,
            "facilities": ["WiFi", "Beach Access", "Bar", "Events", "Water Sports"],
        },
        {
            "owner_id": owners[3].id,
            "name": "Tech Hub Hostel",
            "description": "Hostel designed for digital nomads and tech professionals",
            "address": "100 Feet Road 321",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "zipcode": "560038",
            "photos_urls": ["https://example.com/hostel4_1.jpg", "https://example.com/hostel4_2.jpg"],
            "bank_account_number": "4567890123456789",
            "bank_ifsc_code": "ICIC0001234",
            "bank_name": "ICICI Bank",
            "bank_account_holder_name": "Sneha Gupta",
            "upi_id": "sneha.gupta@upi",
            "is_cash": False,
            "facilities": ["High Speed WiFi", "Work Desks", "Charging Points", "Meeting Room", "Cafe"],
        },
        {
            "owner_id": owners[4].id,
            "name": "Heritage Hostel",
            "description": "Traditional yet modern hostel near historical sites",
            "address": "Avenue Road 654",
            "city": "Gurgaon",
            "state": "Haryana",
            "country": "India",
            "zipcode": "122001",
            "photos_urls": ["https://example.com/hostel5_1.jpg", "https://example.com/hostel5_2.jpg"],
            "bank_account_number": "5678901234567890",
            "bank_ifsc_code": "AXIS0001234",
            "bank_name": "Axis Bank",
            "bank_account_holder_name": "Vikram Sharma",
            "upi_id": "vikram.sharma@upi",
            "is_cash": True,
            "facilities": ["WiFi", "Library", "Museum Tours", "Cultural Events", "Restaurant"],
        },
    ]
    
    hostels = []
    for data in hostels_data:
        # Check if hostel already exists
        existing = db.query(Hostel).filter(Hostel.name == data["name"]).first()
        if not existing:
            hostel = Hostel(**data)
            db.add(hostel)
            hostels.append(hostel)
    
    db.commit()
    print(f"✓ Created {len(hostels)} demo hostel records")
    return hostels


def seed_room_types(db: Session):
    """Create demo room type records"""
    room_types_data = [
        {
            "name": "Single",
            "description": "Room with one bed for individual occupancy",
        },
        {
            "name": "Double",
            "description": "Room with two beds for shared occupancy",
        },
        {
            "name": "Triple",
            "description": "Room with three beds for shared occupancy",
        },
        {
            "name": "Dormitory",
            "description": "Large room with multiple beds for budget travelers",
        },
        {
            "name": "Family",
            "description": "Room suitable for families with multiple beds",
        },
    ]
    
    room_types = []
    for data in room_types_data:
        # Check if room type already exists
        existing = db.query(RoomType).filter(RoomType.name == data["name"]).first()
        if not existing:
            room_type = RoomType(**data)
            db.add(room_type)
            room_types.append(room_type)
    
    db.commit()
    print(f"✓ Created {len(room_types)} demo room type records")
    return room_types


def seed_rooms(db: Session):
    """Create 5 demo room records linked to hostels"""
    hostels = db.query(Hostel).all()
    room_types = db.query(RoomType).all()
    if not hostels:
        print("No hostels found. Please seed hostels first.")
        return []
    if not room_types:
        print("No room types found. Please seed room types first.")
        return []
    
    beds_count = [1, 2, 3, 6, 4]
    
    rooms = []
    for idx, hostel in enumerate(hostels):
        for room_num in range(1, 6):  # 5 rooms per hostel
            room_type_id = room_types[room_num - 1].id
            no_of_beds = beds_count[room_num - 1]
            no_of_occupied = random.randint(0, no_of_beds)
            
            room_data = {
                "hostel_id": hostel.id,
                "room_number": f"{hostel.id}0{room_num}",
                "room_type": room_type_id,
                "no_of_beds": no_of_beds,
                "no_of_occupied_beds": no_of_occupied,
            }
            
            # Check if room already exists
            existing = db.query(Room).filter(
                Room.hostel_id == hostel.id,
                Room.room_number == room_data["room_number"]
            ).first()
            if not existing:
                room = Room(**room_data)
                db.add(room)
                rooms.append(room)
    
    db.commit()
    print(f"✓ Created {len(rooms)} demo room records (5 per hostel)")
    return rooms


def seed_tenants(db: Session):
    """Create demo tenant records linked to rooms"""
    rooms = db.query(Room).all()
    hostels = db.query(Hostel).all()
    if not rooms or not hostels:
        print("No rooms or hostels found. Please seed rooms and hostels first.")
        return []
    
    tenant_names = [
        ("Rahul Sharma", "rahul.sharma@email.com", "+919876543215"),
        ("Priya Patel", "priya.patel@email.com", "+919876543216"),
        ("Amit Kumar", "amit.kumar@email.com", "+919876543217"),
        ("Sneha Singh", "sneha.singh@email.com", "+919876543218"),
        ("Vikram Gupta", "vikram.gupta@email.com", "+919876543219"),
        ("Anjali Verma", "anjali.verma@email.com", "+919876543220"),
        ("Rohit Jain", "rohit.jain@email.com", "+919876543221"),
        ("Kavita Rao", "kavita.rao@email.com", "+919876543222"),
        ("Suresh Reddy", "suresh.reddy@email.com", "+919876543223"),
        ("Meera Iyer", "meera.iyer@email.com", "+919876543224"),
    ]
    
    tenants = []
    for idx, (name, email, phone) in enumerate(tenant_names):
        # Assign to a random room that has available beds
        available_rooms = [r for r in rooms if r.no_of_occupied_beds < r.no_of_beds]
        if not available_rooms:
            continue
        
        room = random.choice(available_rooms)
        hostel = next(h for h in hostels if h.id == room.hostel_id)
        
        tenant_data = {
            "name": name,
            "email": email,
            "phone_number": phone,
            "emergency_contact_name": f"Emergency Contact {idx+1}",
            "emergency_contact_phone": f"+919876543{225+idx}",
            "emergency_contact_relationship": "Parent",
            "gender": random.choice(["Male", "Female"]),
            "photo_url": f"https://example.com/tenant{idx+1}.jpg",
            "aadhaar_number": f"1234567890{idx+10:02d}",
            "identity_verified": random.choice([True, False]),
            "rent": random.randint(3000, 8000),
            "room_id": room.id,
            "hostel_id": hostel.id,
            "join_date": datetime.now() - timedelta(days=random.randint(0, 365)),
            "alternate_phone_number": f"+919876543{235+idx}",
            "address": f"Address {idx+1}",
            "city": hostel.city,
            "state": hostel.state,
            "country": hostel.country,
            "security_deposit": random.randint(5000, 15000),
            "zipcode": hostel.zipcode,
        }
        
        # Check if tenant already exists
        existing = db.query(Tenant).filter(Tenant.phone_number == phone).first()
        if not existing:
            tenant = Tenant(**tenant_data)
            db.add(tenant)
            tenants.append(tenant)
            
            # Update room occupancy
            room.no_of_occupied_beds += 1
            db.add(room)
    
    db.commit()
    print(f"✓ Created {len(tenants)} demo tenant records")
    return tenants



def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...\n")
    
    db = SessionLocal()
    try:
        # Seed data
        seed_owners(db)
        seed_hostels(db)
        seed_room_types(db)
        seed_rooms(db)
        seed_tenants(db)
        
        print("\n✅ Database seeding completed successfully!")
        print("\nDemo Data Summary:")
        print(f"  • Owners: 5")
        print(f"  • Hostels: 5")
        print(f"  • Room Types: 5")
        print(f"  • Rooms: 25 (5 per hostel)")
        print(f"  • Tenants: ~10 (based on room availability)")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
