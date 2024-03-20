"""
The command-line interface for this importer
"""

from .main import import_data
# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

def main():
    import_data()

if __name__ == "__main__":
    main()