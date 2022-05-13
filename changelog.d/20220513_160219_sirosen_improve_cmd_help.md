### Enhancements

* Commands which have required arguments will print their helptext if invoked
  with no arguments. They still `exit(2)` (usage error). This only applies to
  the case of a command with required arguments being called with no arguments
  at all.
