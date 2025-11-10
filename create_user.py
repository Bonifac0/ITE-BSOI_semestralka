import hashlib
import getpass

def hash_password(password):
    """Hashes a password using SHA256. Must be identical to the one in run_webserver.py."""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    """Generates an SQL INSERT statement for a new user."""
    print("--- Create New Dashboard User ---")
    
    try:
        username = input("Enter username: ")
        password = getpass.getpass("Enter password: ")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return
    
    if not username or not password:
        print("\nUsername and password cannot be empty.")
        return

    password_hash = hash_password(password)
    
    # Basic escaping to handle single quotes in username
    username_escaped = username.replace("'", "''")

    sql_command = f"INSERT INTO users (username, password_hash) VALUES ('{username_escaped}', '{password_hash}');"
    
    print("\n" + "="*40)
    print("SQL Command to Create User")
    print("="*40)
    print("\nRun the following command in your database to create the user:\n")
    print(sql_command)
    print("\n" + "="*40)

if __name__ == "__main__":
    main()

