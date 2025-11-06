from datetime import datetime


def log(msg, level="INFO", category=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cat = f"[{category}] " if category else ""
    print(f"[{timestamp}] [{level}] {cat}{msg}")


if __name__ == "__main__":
    log("ssss", level="WARNING", category="AWS")
    log("aaa")
