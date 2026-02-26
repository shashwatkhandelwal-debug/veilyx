# Mock DigiLocker - Simulates real DigiLocker data
# In reality, this data would come from the government's DigiLocker API

mock_database = {
    "user_001": {
        "name": "Rohan Sharma",
        "date_of_birth": "2000-03-15",
        "document_valid": True
    },
    "user_002": {
        "name": "Priya Mehta",
        "date_of_birth": "2005-07-22",
        "document_valid": True
    }
}

def get_user_data(user_id):
    if user_id in mock_database:
        return mock_database[user_id]
    else:
        return None