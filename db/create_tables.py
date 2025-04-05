from src.models.meeting import Meeting

def create_tables():
    print("Creating DynamoDB tables if they don't exist...")
    Meeting.create_table(wait=True, billing_mode="PAY_PER_REQUEST")
    print("All tables created!")

if __name__ == "__main__":
    create_tables()
