#!/usr/bin/env python

"""Kit command line tool.

There are currently 4 commands available via the command tool, all
detailed below.

All commands accept an optional argument ``-c, --conf``
to indicate the path of the configuration file to use. If none is specified
Kit will search in the current directory for possible matches. If a single
file ``.cfg`` file is found it will use it.

"""

from kit.commands import parser

def main():
  """Run command line tool."""
  parsed_args = parser.parse_args()
  parsed_args.handler(parsed_args)


if __name__ == '__main__':
  main()

