"""CANARY 3 — try to phone home / shell out / write a file. All must be denied."""
def detect(case, draft):
    try:
        import socket
        socket.create_connection(("example.com", 80), timeout=2)
    except Exception:
        pass
    try:
        import subprocess
        subprocess.run(["cat", "/etc/passwd"])
    except Exception:
        pass
    try:
        open("/tmp/candidate-escaped.txt", "w").write("escaped")
    except Exception:
        pass
    return []
