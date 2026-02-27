# mock_digilocker.py
# Simulates DigiLocker API responses for testing

mock_database = {
    "user_001": {
        "name": "Rohan Sharma",
        "date_of_birth": "2000-03-15",
        "document_valid": True,
        "city": "Delhi",
        "account_type": "savings"
    },
    "user_002": {
        "name": "Priya Mehta",
        "date_of_birth": "2005-07-22",
        "document_valid": True,
        "city": "Mumbai",
        "account_type": "current"
    },
    "user_003": {
        "name": "Amit Verma",
        "date_of_birth": "1995-11-08",
        "document_valid": True,
        "city": "Bangalore",
        "account_type": "savings"
    },
    "user_004": {
        "name": "Sneha Patel",
        "date_of_birth": "2010-04-30",
        "document_valid": True,
        "city": "Ahmedabad",
        "account_type": "savings"
    },
    "user_005": {
        "name": "Vikram Singh",
        "date_of_birth": "1988-09-14",
        "document_valid": False,
        "city": "Chandigarh",
        "account_type": "current"
    },
    "user_006": {
        "name": "Ananya Krishnan",
        "date_of_birth": "1992-06-21",
        "document_valid": True,
        "city": "Chennai",
        "account_type": "savings"
    },
    "user_007": {
        "name": "Rahul Gupta",
        "date_of_birth": "2008-12-05",
        "document_valid": True,
        "city": "Lucknow",
        "account_type": "savings"
    },
    "user_008": {
        "name": "Deepika Nair",
        "date_of_birth": "1990-03-28",
        "document_valid": True,
        "city": "Hyderabad",
        "account_type": "current"
    },
    "user_009": {
        "name": "Arjun Malhotra",
        "date_of_birth": "1985-07-17",
        "document_valid": False,
        "city": "Pune",
        "account_type": "savings"
    },
    "user_010": {
        "name": "Kavya Reddy",
        "date_of_birth": "2009-01-11",
        "document_valid": True,
        "city": "Hyderabad",
        "account_type": "savings"
    },
    "user_011": {
        "name": "Manish Tiwari",
        "date_of_birth": "1978-08-30",
        "document_valid": True,
        "city": "Kanpur",
        "account_type": "current"
    },
    "user_012": {
        "name": "Riya Joshi",
        "date_of_birth": "2003-05-19",
        "document_valid": True,
        "city": "Jaipur",
        "account_type": "savings"
    }
}

def get_user_data(user_id):
    if user_id in mock_database:
        return mock_database[user_id]
    return None

def get_all_users():
    return list(mock_database.keys())
