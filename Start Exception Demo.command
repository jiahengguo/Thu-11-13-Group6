#!/bin/zsh
# Local simulation only. The existing project environment is reused.
cd -- "${0:A:h}" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  print 'Install the project dependencies using docs/exception/README.md first.'
  read '?Press Enter to exit.'
  exit 1
fi
print 'After startup, open: http://127.0.0.1:8766/#exception-panel'
print 'Select Investigate cancellation or Investigate delay complaint. Press Control+C to stop the server.'
exec .venv/bin/python -m tripmate.api.server --workbench --port 8766
