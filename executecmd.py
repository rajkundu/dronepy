#!/usr/bin/python3

import sys
from textserver import parseCarAction, executeCarAction

def main():
  executeCarAction(parseCarAction(sys.argv[1]))
  return 0

if __name__ == "__main__":
    main()
