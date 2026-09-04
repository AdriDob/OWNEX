import sys
import pytest

if __name__ == '__main__':
    # Run pytest programmatically and forward exit code
    args = sys.argv[1:] or ['-q', '--maxfail=1', '-vv']
    rc = pytest.main(args)
    print('\nPYTEST EXIT CODE:', rc)
    sys.exit(rc)
