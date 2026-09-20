import sys
try:
    from diskcache import Cache
    print("diskcache imported successfully")
except ImportError as e:
    print(f"Import error: {e}")
print(sys.executable)
print(sys.path)
